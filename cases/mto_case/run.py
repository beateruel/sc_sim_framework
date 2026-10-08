from pathlib import Path
import json
import simpy

from datetime import timedelta

from core.mto.resources.resources import Resources
from core.mto.engine.scheduler import Scheduler
from core.mto.workflows.order_flow import run_order_flow
from core.mto.data.loaders import load_orders_from_json, load_config
from core.mto.entities.inventory import inventory_monitor

from core.mto.analytics.kpis.lead_time import compute_lead_time
from core.mto.analytics.kpis.service_level import compute_otif
from core.mto.analytics.kpis.throughput import compute_throughput
from core.mto.analytics.kpis.extractor import orders_to_dataframe
from core.mto.analytics.cost.cost_model import compute_costs
from core.mto.analytics.profit.profit_model import compute_profit
from core.mto.analytics.environmental.environmental_model import compute_environmental_impact
from core.mto.analytics.visualization.gantt import plot_gantt_clean
from core.mto.analytics.visualization.plot_inventory import plot_inventory


def load_case_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def sim_to_date(sim_time, base_date):
    return base_date + timedelta(hours=sim_time)


def create_output_folders(base_path: Path) -> None:
    for folder in [
        "kpis",
        "cost",
        "profit",
        "events",
        "emissions",
        "visualization",
    ]:
        (base_path / folder).mkdir(parents=True, exist_ok=True)


def main() -> None:
    case_path = Path(__file__).resolve().parent
    case_config = load_case_config(case_path / "config.json")

    scenario = case_config["scenario"]
    data_path = case_path / "data"
    results_path = Path(case_config["outputs"]["base_results_dir"]) / scenario
    create_output_folders(results_path)

    orders_path = data_path / case_config["input_files"]["orders"]
    process_config_path = data_path / case_config["input_files"]["process_config"]

    orders = load_orders_from_json(str(orders_path))
    config = load_config(str(process_config_path))

    prototyping_type = case_config["simulation"]["prototyping_type"]
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
        print(f"{order.id} arrives at hour {delay}")

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

    print("\nFinal states:")
    for order in completed_orders:
        print(order.id, order.start_times, order.end_times)

    df_lead = compute_lead_time(completed_orders)
    df_lead.to_csv(results_path / "kpis" / "lead_time.csv", index=False)

    df_otif, service_level = compute_otif(completed_orders, first_date)
    df_otif.to_csv(results_path / "kpis" / "otif.csv", index=False)
    print("Service level:", service_level)

    df_throughput = compute_throughput(completed_orders)
    if hasattr(df_throughput, "to_csv"):
        df_throughput.to_csv(results_path / "kpis" / "throughput.csv", index=False)

    df_events = orders_to_dataframe(completed_orders)
    df_events.to_csv(results_path / "events" / "events.csv", index=False)

    df_costs = compute_costs(completed_orders, config)
    df_costs.to_csv(results_path / "cost" / "costs.csv", index=False)
    print("Costs:", df_costs)

    df_profit = compute_profit(completed_orders, first_date)
    df_profit.to_csv(results_path / "profit" / "profit.csv", index=False)
    print("Profit:", df_profit)

    df_emissions = compute_environmental_impact(completed_orders, config)
    df_emissions.to_csv(results_path / "emissions" / "emissions.csv", index=False)
    print("Emissions:", df_emissions)

    if case_config["outputs"]["save_gantt"]:
        plot_gantt_clean(
            completed_orders,
            first_date,
            save_path=str(results_path / "visualization" / "gantt.png"),
        )

    if case_config["outputs"]["save_inventory_plots"]:
        resources.sample_log.append((0, resources.sample_inventory.level))
        resources.production_log.append((0, resources.production_inventory.level))

        plot_inventory(
            resources.sample_log,
            first_date,
            title="Sample Inventory",
            reorder_point=config["operational"]["sample_reorder_point_units"],
        )

        plot_inventory(
            resources.production_log,
            first_date,
            title="Production Inventory",
        )

    print(f"\nResults saved in: {results_path}")


if __name__ == "__main__":
    main()