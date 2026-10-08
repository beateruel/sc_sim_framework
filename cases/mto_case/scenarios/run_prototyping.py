from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from datetime import timedelta
import json

import pandas as pd
import simpy

from core.mto.resources.resources import Resources
from core.mto.engine.scheduler import Scheduler
from core.mto.workflows.order_flow import run_order_flow
from core.mto.data.loaders import load_orders_from_json, load_config
from core.mto.entities.inventory import inventory_monitor

from core.mto.analytics.kpis.lead_time import compute_lead_time
from core.mto.analytics.kpis.service_level import compute_otif
from core.mto.analytics.kpis.throughput import compute_throughput
from core.mto.analytics.cost.cost_model import compute_costs
from core.mto.analytics.profit.profit_model import compute_profit
from core.mto.analytics.environmental.environmental_model import (
    compute_environmental_impact,
)
from core.mto.analytics.visualization.gantt import plot_gantt_clean
from core.mto.analytics.visualization.plot_inventory import plot_inventory


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def sim_to_date(sim_time, base_date):
    return base_date + timedelta(hours=sim_time)


def run_single_scenario(
    case_config: dict,
    process_config: dict,
    orders_path: Path,
    prototyping_type: str,
):
    orders = load_orders_from_json(str(orders_path))

    config = deepcopy(process_config)
    simulation_until = case_config["simulation"]["until"]

    env = simpy.Environment()
    scheduler = Scheduler(env)
    resources = Resources(env, config)

    orders.sort(key=lambda order: order.init_date)

    first_date = orders[0].init_date
    config["base_date"] = first_date

    env.process(inventory_monitor(env, resources, config))

    scheduled_orders = []

    for order in orders:
        order.prototyping_type = prototyping_type
        delay = (order.init_date - first_date).days * 24
        scheduled_orders.append((delay, order))

    scheduler.schedule_orders_with_arrivals(
        scheduled_orders,
        lambda order: run_order_flow(env, order, resources, config),
    )

    env.run(until=simulation_until)

    completed_orders = [order for _, order in scheduled_orders]

    for order in completed_orders:
        order.start_dates = {
            key: sim_to_date(value, first_date)
            for key, value in order.start_times.items()
        }

        order.end_dates = {
            key: sim_to_date(value, first_date)
            for key, value in order.end_times.items()
        }

    return completed_orders, resources, config, first_date


def extract_kpis(
    scenario_name: str,
    prototyping_type: str,
    completed_orders,
    process_config: dict,
    first_date,
) -> dict:
    df_lead = compute_lead_time(completed_orders)

    df_otif, service_level = compute_otif(
        completed_orders,
        first_date,
    )

    throughput = compute_throughput(completed_orders)

    df_costs = compute_costs(
        completed_orders,
        process_config,
    )

    df_profit = compute_profit(
        completed_orders,
        first_date,
    )

    df_emissions = compute_environmental_impact(
        completed_orders,
        process_config,
    )
    total_waste = _safe_sum(df_emissions, "waste")
    average_waste = _safe_mean(df_emissions, "waste")
    total_cost = _safe_sum(df_profit, "total_cost")

    total_committed_revenue = _safe_sum(
        df_profit,
        "committed_revenue",
    )

    total_recognized_revenue = _safe_sum(
        df_profit,
        "recognized_revenue",
    )

    total_committed_profit = _safe_sum(
        df_profit,
        "committed_profit",
    )

    total_recognized_profit = _safe_sum(
        df_profit,
        "recognized_profit",
    )

    lead_time_hours = _safe_mean(df_lead, "lead_time_hours")

    return {
        "scenario": scenario_name,
        "prototyping_type": prototyping_type,
        "service_level": service_level,
        "service_level_percent": service_level * 100,
        "average_lead_time_hours": lead_time_hours,
        "average_lead_time_days": (
            lead_time_hours / 24
            if lead_time_hours is not None
            else None
        ),
        "throughput_orders_per_hour": throughput,
        "throughput_orders_per_day": (
            throughput * 24
            if throughput is not None
            else None
        ),
        "total_cost": total_cost,
        "total_committed_revenue": total_committed_revenue,
        "total_recognized_revenue": total_recognized_revenue,
        "total_committed_profit": total_committed_profit,
        "total_recognized_profit": total_recognized_profit,
        "committed_profit_margin": (
            total_committed_profit / total_committed_revenue
            if total_committed_revenue not in [None, 0]
            else None
        ),
        "recognized_profit_margin": (
            total_recognized_profit / total_recognized_revenue
            if total_recognized_revenue not in [None, 0]
            else None
        ),
        "lost_revenue_due_to_late_orders": (
            total_committed_revenue - total_recognized_revenue
            if total_committed_revenue is not None
            and total_recognized_revenue is not None
            else None
        ),
        "total_emissions": _numeric_sum(df_emissions),
        "total_waste": total_waste,
        "average_waste": average_waste,
        "completed_orders": _completed_orders(completed_orders),
        "total_orders": len(completed_orders),
    }


def save_visualizations(
    scenario_name: str,
    completed_orders,
    resources,
    case_config: dict,
    process_config: dict,
    first_date,
    visualization_dir: Path,
) -> None:
    scenario_dir = visualization_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    if case_config["outputs"].get("save_gantt", True):
        plot_gantt_clean(
            completed_orders,
            first_date,
            save_path=str(scenario_dir / "gantt.png"),
        )

    if case_config["outputs"].get("save_inventory_plots", True):
        resources.sample_log.append((0, resources.sample_inventory.level))
        resources.production_log.append((0, resources.production_inventory.level))

        plot_inventory(
            resources.sample_log,
            first_date,
            title=f"Sample Inventory - {scenario_name}",
            reorder_point=process_config["operational"][
                "sample_reorder_point_units"
            ],
        )

        plot_inventory(
            resources.production_log,
            first_date,
            title=f"Production Inventory - {scenario_name}",
        )


def build_scenario_name(prototyping_type: str) -> str:
    if prototyping_type.upper() == "PHYSICAL":
        return "baseline"

    return prototyping_type.lower()


def _safe_mean(df: pd.DataFrame, column: str):
    if df is None or df.empty or column not in df.columns:
        return None

    return df[column].mean()


def _safe_sum(df: pd.DataFrame, column: str):
    if df is None or df.empty or column not in df.columns:
        return None

    return df[column].sum()


def _numeric_sum(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return None

    return numeric_df.sum().sum()


def _completed_orders(orders) -> int:
    return sum(
        1
        for order in orders
        if hasattr(order, "finish_time")
        and order.finish_time is not None
    )


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    case_dir = scenario_dir.parent
    project_root = case_dir.parents[1]

    scenarios_config = load_json(scenario_dir / "scenarios_config.json")

    paths = scenarios_config["paths"]

    case_config_path = project_root / paths["case_config"]
    case_data_dir = project_root / paths["case_data_dir"]

    case_config = load_json(case_config_path)

    orders_path = case_data_dir / case_config["input_files"]["orders"]

    process_config_path = (
        case_data_dir
        / case_config["input_files"]["process_config"]
    )

    process_config = load_config(str(process_config_path))

    output_dir = (
        project_root
        / "results"
        / "experiments"
        / "mto_case"
    )

    visualization_root = output_dir / "visualization"

    output_dir.mkdir(parents=True, exist_ok=True)
    visualization_root.mkdir(parents=True, exist_ok=True)

    prototyping_config = scenarios_config["prototyping"]

    visualization_dir = (
        visualization_root
        / prototyping_config["visualization_subdir"]
    )

    visualization_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for prototyping_type in prototyping_config["types"]:
        scenario_name = build_scenario_name(prototyping_type)

        print(f"Running {scenario_name}...")

        completed_orders, resources, config, first_date = run_single_scenario(
            case_config=case_config,
            process_config=process_config,
            orders_path=orders_path,
            prototyping_type=prototyping_type,
        )

        rows.append(
            extract_kpis(
                scenario_name=scenario_name,
                prototyping_type=prototyping_type,
                completed_orders=completed_orders,
                process_config=config,
                first_date=first_date,
            )
        )

        if prototyping_config.get("save_plots", True):
            save_visualizations(
                scenario_name=scenario_name,
                completed_orders=completed_orders,
                resources=resources,
                case_config=case_config,
                process_config=config,
                first_date=first_date,
                visualization_dir=visualization_dir,
            )

    df_results = pd.DataFrame(rows)

    output_file = output_dir / prototyping_config["output_file"]

    df_results.to_csv(output_file, index=False)

    print(f"Results saved in: {output_file}")
    print(f"Visualizations saved in: {visualization_dir}")


if __name__ == "__main__":
    main()