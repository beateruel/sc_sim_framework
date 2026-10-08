# cases/mts_case/run.py

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

from core.mts.analytics.visualization.visualization import (
    plot_mts_raw_material_inventory,
    plot_mts_inventory_individual,
    plot_mts_finished_goods,
    plot_mts_demand,
)

from core.mts.analytics.kpis.service_level import (
    compute_mts_otif,
    compute_mts_fill_rate,
    compute_mts_fill_rate_summary,
    compute_mts_stockout_rate,
)
from core.mts.analytics.kpis.inventory import (
    compute_average_inventory,
    compute_inventory_turnover,
    compute_inventory_variability,
    compute_inventory_peaks,
)
from core.mts.analytics.kpis.throughput import (
    compute_mts_throughput,
    compute_total_throughput,
    compute_production_plan_fulfillment,
    compute_production_lead_time,
)
from core.mts.analytics.cost.cost_model import compute_mts_costs
from core.mts.analytics.profit.profit_model import compute_mts_profit
from core.mts.analytics.environmental.environmental_model import (
    compute_mts_environmental_impact,
)


def load_case_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_output_folders(results_path: Path) -> dict:
    folders = {
        "kpis": results_path / "kpis",
        "cost": results_path / "cost",
        "profit": results_path / "profit",
        "emissions": results_path / "emissions",
        "operations": results_path / "operations",
        "visualization": results_path / "visualization",
    }

    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)

    return folders


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


def save_operation_results(
    results: dict,
    weekly_demand: pd.DataFrame,
    operations_path: Path,
) -> None:
    results["inventory"].to_csv(
        operations_path / "inventory.csv",
        index=False,
    )

    results["purchase_orders"].to_csv(
        operations_path / "purchase_orders.csv",
        index=False,
    )

    results["releases"].to_csv(
        operations_path / "releases.csv",
        index=False,
    )

    results["production"].to_csv(
        operations_path / "production.csv",
        index=False,
    )

    results["distribution"].to_csv(
        operations_path / "distribution.csv",
        index=False,
    )

    results["weekly_metrics"].to_csv(
        operations_path / "weekly_metrics.csv",
        index=False,
    )

    weekly_demand.to_csv(
        operations_path / "weekly_demand.csv",
        index=False,
    )


def load_operation_results(operations_path: Path) -> dict:
    return {
        "inventory": pd.read_csv(operations_path / "inventory.csv"),
        "purchase_orders": pd.read_csv(operations_path / "purchase_orders.csv"),
        "releases": pd.read_csv(operations_path / "releases.csv"),
        "production": pd.read_csv(operations_path / "production.csv"),
        "distribution": pd.read_csv(operations_path / "distribution.csv"),
        "weekly_metrics": pd.read_csv(operations_path / "weekly_metrics.csv"),
        "weekly_demand": pd.read_csv(operations_path / "weekly_demand.csv"),
    }


def save_kpis(results: dict, folders: dict) -> None:
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

    df_inventory_variability = compute_inventory_variability(
        results["inventory"],
    )

    df_inventory_peaks = compute_inventory_peaks(
        results["inventory"],
    )

    df_throughput = compute_mts_throughput(
        results["production"],
    )

    df_total_throughput = compute_total_throughput(
        results["production"],
    )

    df_production_plan_fulfillment = compute_production_plan_fulfillment(
        results["production"],
    )

    df_production_lead_time = compute_production_lead_time(
        results["production"],
    )

    df_otif.to_csv(folders["kpis"] / "otif.csv", index=False)
    df_fill_rate.to_csv(folders["kpis"] / "fill_rate.csv", index=False)
    df_fill_rate_summary.to_csv(
        folders["kpis"] / "fill_rate_summary.csv",
        index=False,
    )
    df_stockouts.to_csv(folders["kpis"] / "stockouts.csv", index=False)
    df_avg_inventory.to_csv(folders["kpis"] / "average_inventory.csv", index=False)

    df_inventory_turnover.to_csv(
        folders["kpis"] / "inventory_turnover.csv",
        index=False,
    )

    df_inventory_variability.to_csv(
        folders["kpis"] / "inventory_variability.csv",
        index=False,
    )

    df_inventory_peaks.to_csv(
        folders["kpis"] / "inventory_peaks.csv",
        index=False,
    )

    df_throughput.to_csv(
        folders["kpis"] / "throughput.csv",
        index=False,
    )

    df_total_throughput.to_csv(
        folders["kpis"] / "total_throughput.csv",
        index=False,
    )

    df_production_plan_fulfillment.to_csv(
        folders["kpis"] / "production_plan_fulfillment.csv",
        index=False,
    )

    df_production_lead_time.to_csv(
        folders["kpis"] / "production_lead_time.csv",
        index=False,
    )

    pd.DataFrame(
        [
            {
                "service_level": service_level,
                "service_level_percent": service_level * 100,
            }
        ]
    ).to_csv(
        folders["kpis"] / "service_level.csv",
        index=False,
    )


def save_cost_profit_emissions(
    results: dict,
    config: dict,
    folders: dict,
) -> None:
    df_costs = compute_mts_costs(
        purchase_orders_df=results["purchase_orders"],
        production_df=results["production"],
        distribution_df=results["distribution"],
        inventory_df=results["inventory"],
        holding_rate=config["costs"]["holding_rate"],
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

    df_costs.to_csv(folders["cost"] / "costs.csv", index=False)
    df_profit.to_csv(folders["profit"] / "profit.csv", index=False)
    df_emissions.to_csv(folders["emissions"] / "emissions.csv", index=False)


def save_visualizations(
    results: dict,
    config: dict,
    folders: dict,
) -> None:
    if not config["outputs"]["save_plots"]:
        return

    show_plots = config["outputs"]["show_plots"]
    plot_config = config["plots"]

    material_id = plot_config["raw_material_id"]
    material_label = plot_config.get("raw_material_label", material_id)

    product_ids = plot_config["product_ids"]
    product_labels = plot_config["product_labels"]

    plot_mts_raw_material_inventory(
        inventory_df=results["inventory"],
        material_id=material_id,
        material_label=material_label,
        output_path=folders["visualization"] / "inventory_oh_it_raw_material.png",
        show=show_plots,
    )

    plot_mts_inventory_individual(
        inventory_df=results["inventory"],
        weekly_demand=results["weekly_demand"],
        material_id=material_id,
        material_label=material_label,
        product_ids=product_ids,
        product_labels=product_labels,
        output_path=folders["visualization"] / "inventory_individual.png",
        show=show_plots,
    )

    plot_mts_finished_goods(
        inventory_df=results["inventory"],
        product_ids=product_ids,
        product_labels=product_labels,
        output_path=folders["visualization"] / "finished_goods.png",
        show=show_plots,
    )

    plot_mts_demand(
        weekly_demand=results["weekly_demand"],
        output_path=folders["visualization"] / "weekly_demand.png",
        show=show_plots,
    )


def main() -> None:
    case_path = Path(__file__).resolve().parent
    config = load_case_config(case_path / "config.json")

    scenario = config["scenario"]
    data_path = case_path / "data"

    results_path = Path(config["outputs"]["base_results_dir"]) / scenario
    folders = create_output_folders(results_path)

    weekly_demand = load_weekly_demand_mts(
        data_path / config["input_files"]["demand"],
        variation=config["simulation"]["demand_variation"],
    )

    products_bom = load_products_bom(
        data_path / config["input_files"]["bom"],
    )

    suppliers = load_suppliers(
        data_path / config["input_files"]["suppliers"],
    )

    material_prices = build_material_prices(config)

    mts_policy = config["mts_policy"]
    costs = config["costs"]
    emissions = config["emissions"]
    time = config["time"]

    mts_config = MTSConfig(
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

    runner = MTSSimulationRunner(
        weekly_demand=weekly_demand,
        products_bom=products_bom,
        suppliers=suppliers,
        material_prices=material_prices,
        config=mts_config,
        shortage_start_week=config["simulation"]["shortage_start_week"],
        shortage_end_week=config["simulation"]["shortage_end_week"],
        initial_raw_material_inventory=config["initial_inventory"]["raw_material"],
        initial_finished_goods_inventory=config["initial_inventory"][
            "finished_goods"
        ],
    )

    summary = runner.run()
    results = runner.get_results()

    print("\n========== SIMULATION SUMMARY ==========")
    for key, value in summary.items():
        print(f"{key}: {round(value, 2)}")

    save_operation_results(
        results=results,
        weekly_demand=weekly_demand,
        operations_path=folders["operations"],
    )

    results_from_files = load_operation_results(
        operations_path=folders["operations"],
    )

    save_kpis(
        results=results_from_files,
        folders=folders,
    )

    save_cost_profit_emissions(
        results=results_from_files,
        config=config,
        folders=folders,
    )

    save_visualizations(
        results=results_from_files,
        config=config,
        folders=folders,
    )

    print(f"\nResults saved in: {results_path}")


if __name__ == "__main__":
    main()