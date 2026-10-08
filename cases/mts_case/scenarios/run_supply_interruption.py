from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import pandas as pd

from core.mts.data.loaders import (
    load_products_bom,
    load_suppliers,
    load_weekly_demand_mts,
)
from core.mts.engine.scheduler import MTSConfig
from core.mts.simulation.runner import MTSSimulationRunner

from core.mts.analytics.kpis.service_level import (
    compute_mts_otif,
    compute_mts_fill_rate,
    compute_mts_fill_rate_summary,
    compute_mts_stockout_rate,
)
from core.mts.analytics.kpis.inventory import (
    compute_average_inventory,
    compute_inventory_turnover,
)
from core.mts.analytics.kpis.throughput import (
    compute_production_plan_fulfillment,
    compute_production_lead_time,
)
from core.mts.analytics.cost.cost_model import compute_mts_costs
from core.mts.analytics.profit.profit_model import compute_mts_profit
from core.mts.analytics.environmental.environmental_model import (
    compute_mts_environmental_impact,
)
from core.mts.analytics.visualization.visualization import (
    plot_mts_raw_material_inventory,
    plot_mts_inventory_individual,
    plot_mts_finished_goods,
    plot_mts_demand,
)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_material_prices(config: dict) -> dict:
    price_config = config["material_prices"]

    if price_config["mode"] == "linear":
        return {
            month: price_config["base_price"]
            + month * price_config["monthly_increment"]
            for month in range(price_config["months"])
        }

    if price_config["mode"] == "fixed":
        return {
            month: price_config["price"]
            for month in range(price_config["months"])
        }

    raise ValueError(f"Unknown material price mode: {price_config['mode']}")


def build_mts_config(config: dict) -> MTSConfig:
    mts_policy = config["mts_policy"]
    costs = config["costs"]
    emissions = config["emissions"]
    time = config["time"]

    return MTSConfig(
        labour_cost_per_hour=costs["labour_cost_per_hour"],
        ordering_cost=costs["ordering_cost"],
        holding_rate=costs["holding_rate"],
        product_price=costs["product_price"],
        client_transport_time_hours=time["client_transport_time_hours"],
        client_storage_time_hours=time["client_storage_time_hours"],
        client_distribution_cost=costs["client_distribution_cost"],
        client_distribution_emissions=emissions["client_distribution_emissions"],
        weeks_per_month=mts_policy["weeks_per_month"],
        purchase_cycle_weeks=mts_policy["purchase_cycle_weeks"],
        demand_coverage_weeks=mts_policy["demand_coverage_weeks"],
        distributor_release_cycle_weeks=mts_policy[
            "distributor_release_cycle_weeks"
        ],
    )


def run_single_scenario(
    case_config: dict,
    case_data_dir: Path,
    shortage_start_week: int,
    shortage_end_week: int,
) -> tuple[dict, dict, pd.DataFrame]:
    config = deepcopy(case_config)

    config["simulation"]["demand_variation"] = 0.0
    config["simulation"]["shortage_start_week"] = shortage_start_week
    config["simulation"]["shortage_end_week"] = shortage_end_week

    weekly_demand = load_weekly_demand_mts(
        case_data_dir / config["input_files"]["demand"],
        variation=config["simulation"]["demand_variation"],
    )

    products_bom = load_products_bom(
        case_data_dir / config["input_files"]["bom"],
    )

    suppliers = load_suppliers(
        case_data_dir / config["input_files"]["suppliers"],
    )

    runner = MTSSimulationRunner(
        weekly_demand=weekly_demand,
        planning_demand=weekly_demand,
        products_bom=products_bom,
        suppliers=suppliers,
        material_prices=build_material_prices(config),
        config=build_mts_config(config),
        shortage_start_week=config["simulation"]["shortage_start_week"],
        shortage_end_week=config["simulation"]["shortage_end_week"],
        initial_raw_material_inventory=config["initial_inventory"]["raw_material"],
        initial_finished_goods_inventory=config["initial_inventory"][
            "finished_goods"
        ],
    )

    summary = runner.run()
    results = runner.get_results()

    return summary, results, weekly_demand


def extract_kpis(
    scenario_name: str,
    shortage_start_week: int,
    shortage_end_week: int,
    summary: dict,
    results: dict,
    case_config: dict,
) -> dict:
    df_otif, service_level = compute_mts_otif(
        results["distribution"],
    )

    df_fill_rate = compute_mts_fill_rate(
        results["distribution"],
    )

    df_fill_rate_summary = compute_mts_fill_rate_summary(
        results["distribution"],
    )

    df_stockouts = compute_mts_stockout_rate(
        results["inventory"],
    )

    df_avg_inventory = compute_average_inventory(
        results["inventory"],
    )

    df_inventory_turnover = compute_inventory_turnover(
        results["inventory"],
        results["distribution"],
    )

    df_production_plan_fulfillment = compute_production_plan_fulfillment(
        results["production"],
    )

    df_production_lead_time = compute_production_lead_time(
        results["production"],
    )

    df_costs = compute_mts_costs(
        purchase_orders_df=results["purchase_orders"],
        production_df=results["production"],
        distribution_df=results["distribution"],
        inventory_df=results["inventory"],
        holding_rate=case_config["costs"]["holding_rate"],
    )

    df_profit = compute_mts_profit(
        distribution_df=results["distribution"],
        cost_df=df_costs,
    )

    df_emissions = compute_mts_environmental_impact(
        purchase_orders_df=results["purchase_orders"],
        distribution_df=results["distribution"],
        production_df=results["production"],
    )

    duration_weeks = (
        shortage_end_week - shortage_start_week
        if shortage_start_week >= 0 and shortage_end_week >= 0
        else 0
    )

    return {
        "scenario": scenario_name,
        "shortage_start_week": shortage_start_week,
        "shortage_end_week": shortage_end_week,
        "shortage_duration_weeks": duration_weeks,
        "service_level": service_level,
        "service_level_percent": service_level * 100,
        "otif_mean": _safe_mean(df_otif, "otif"),
        "fill_rate_mean": _safe_mean(df_fill_rate, "fill_rate"),
        "fill_rate_global": _get_first_numeric(
            df_fill_rate_summary,
            "fill_rate",
        ),
        "fill_rate_global_percent": _get_first_numeric(
            df_fill_rate_summary,
            "fill_rate_percent",
        ),
        "requested_quantity": _get_first_numeric(
            df_fill_rate_summary,
            "requested_quantity",
        ),
        "shipped_quantity": _get_first_numeric(
            df_fill_rate_summary,
            "shipped_quantity",
        ),
        "unfilled_quantity": _get_first_numeric(
            df_fill_rate_summary,
            "unfilled_quantity",
        ),
        "stockout_rate": _get_first_numeric(
            df_stockouts,
            "stockout_rate",
        ),
        "stockout_rate_percent": _get_first_numeric(
            df_stockouts,
            "stockout_rate_percent",
        ),
        "average_raw_material_oh": _get_first_numeric(
        df_avg_inventory,
        "average_raw_material_oh",
        ),
        "average_raw_material_it": _get_first_numeric(
            df_avg_inventory,
            "average_raw_material_it",
        ),
        "average_finished_goods": _get_first_numeric(
            df_avg_inventory,
            "average_finished_goods",
        ),
        "average_total_inventory": _get_first_numeric(
            df_avg_inventory,
            "average_total_inventory",
        ),
        "inventory_turnover_mean": _numeric_mean(df_inventory_turnover),
        "production_plan_fulfillment": _get_first_numeric(
            df_production_plan_fulfillment,
            "production_plan_fulfillment",
        ),
        "production_plan_fulfillment_percent": _get_first_numeric(
            df_production_plan_fulfillment,
            "production_plan_fulfillment_percent",
        ),
        "production_lead_time_mean": _get_first_numeric(
            df_production_lead_time,
            "average_production_time_hours",
        ),
        "total_cost": _get_first_numeric(df_costs, "total_cost"),
        "total_profit": _get_first_numeric(df_profit, "total_profit"),
        "profit_margin": _get_first_numeric(df_profit, "profit_margin"),
        "total_emissions": _numeric_sum(df_emissions),
        "summary_total_income": summary.get("total_income"),
        "summary_total_cost": summary.get("total_cost"),
        "summary_total_profit": summary.get("total_profit"),
    }


def save_visualizations(
    scenario_name: str,
    results: dict,
    weekly_demand: pd.DataFrame,
    case_config: dict,
    visualization_dir: Path,
) -> None:
    plot_config = case_config["plots"]

    material_id = plot_config["raw_material_id"]
    material_label = plot_config.get("raw_material_label", material_id)
    product_ids = plot_config["product_ids"]
    product_labels = plot_config["product_labels"]

    scenario_dir = visualization_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    plot_mts_raw_material_inventory(
        inventory_df=results["inventory"],
        material_id=material_id,
        material_label=material_label,
        output_path=scenario_dir / "raw_material_inventory.png",
        show=False,
    )

    plot_mts_inventory_individual(
        inventory_df=results["inventory"],
        weekly_demand=weekly_demand,
        material_id=material_id,
        material_label=material_label,
        product_ids=product_ids,
        product_labels=product_labels,
        output_path=scenario_dir / "inventory_individual.png",
        show=False,
    )

    plot_mts_finished_goods(
        inventory_df=results["inventory"],
        product_ids=product_ids,
        product_labels=product_labels,
        output_path=scenario_dir / "finished_goods.png",
        show=False,
    )

    plot_mts_demand(
        weekly_demand=weekly_demand,
        output_path=scenario_dir / "weekly_demand.png",
        show=False,
    )


def _safe_mean(df: pd.DataFrame, column: str):
    if df is None or df.empty or column not in df.columns:
        return None

    return df[column].mean()


def _numeric_mean(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return None

    return numeric_df.mean().mean()


def _numeric_sum(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return None

    return numeric_df.sum().sum()


def _get_first_numeric(df: pd.DataFrame, preferred_column: str):
    if df is None or df.empty:
        return None

    if preferred_column in df.columns:
        return df[preferred_column].iloc[0]

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return None

    return numeric_df.iloc[0, 0]


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    case_dir = scenario_dir.parent
    project_root = case_dir.parents[1]

    scenarios_config = load_json(
        scenario_dir / "scenarios_config.json"
    )

    paths = scenarios_config["paths"]

    case_config_path = project_root / paths["case_config"]
    case_data_dir = project_root / paths["case_data_dir"]

    case_config = load_json(case_config_path)

    output_dir = (
        project_root
        / "results"
        / "experiments"
        / "mts_case"
    )

    visualization_root = output_dir / "visualization"

    output_dir.mkdir(parents=True, exist_ok=True)
    visualization_root.mkdir(parents=True, exist_ok=True)

    shortage_config = scenarios_config["shortage"]

    visualization_dir = (
        visualization_root
        / shortage_config["visualization_subdir"]
    )

    visualization_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for shortage_scenario in shortage_config["scenarios"]:
        scenario_name = shortage_scenario["name"]
        shortage_start_week = shortage_scenario["start_week"]
        shortage_end_week = shortage_scenario["end_week"]

        print(f"Running {scenario_name}...")

        summary, results, weekly_demand = run_single_scenario(
            case_config=case_config,
            case_data_dir=case_data_dir,
            shortage_start_week=shortage_start_week,
            shortage_end_week=shortage_end_week,
        )

        rows.append(
            extract_kpis(
                scenario_name=scenario_name,
                shortage_start_week=shortage_start_week,
                shortage_end_week=shortage_end_week,
                summary=summary,
                results=results,
                case_config=case_config,
            )
        )

        if shortage_config.get("save_plots", True):
            save_visualizations(
                scenario_name=scenario_name,
                results=results,
                weekly_demand=weekly_demand,
                case_config=case_config,
                visualization_dir=visualization_dir,
            )

    df_results = pd.DataFrame(rows)

    output_file = output_dir / shortage_config["output_file"]

    df_results.to_csv(output_file, index=False)

    print(f"Results saved in: {output_file}")
    print(f"Visualizations saved in: {visualization_dir}")


if __name__ == "__main__":
    main()