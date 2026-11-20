"""
Robustness test of the MTO case under stochastic order quantities and durations.

For each demand level (baseline and +30%) the model is run with:
    deterministic : no randomness (reference, one run)
    quantity      : units of each order x (1 + e), e ~ N(0, quantity_cv)
    duration      : duration of approval, design and production activities
                    x lognormal factor (mean 1, CV = duration_cv)
    both          : quantity and duration randomness together

Each stochastic variant is replicated with seeds 0..R-1. The quantity noise
uses the same seed in every variant and demand level (common random numbers).
Transport times are not randomised.

The same variants are also run for PHYSICAL and DIGITAL prototyping at the
baseline demand. Because seeds are common, the paired difference DIGITAL minus
PHYSICAL is computed for each seed (results_robustness_prototyping_paired.csv).

Outputs (results/experiments/mto_case/):
    results_robustness.csv          one row per run
    results_robustness_summary.csv  mean, std, P5 and P95 per scenario/variant
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import simpy

from core.mto.data.loaders import load_config, load_orders_from_json
from core.mto.engine.scheduler import Scheduler
from core.mto.entities.inventory import inventory_monitor
from core.mto.resources.resources import Resources
from core.mto.utils.time_utils import set_duration_noise
from core.mto.workflows.order_flow import run_order_flow

from cases.mto_case.scenarios.run_demand_variation import (
    apply_demand_multiplier,
    build_scenario_name,
    extract_kpis,
    load_json,
    sim_to_date,
)
from copy import deepcopy

VARIANTS = {
    "deterministic": {"quantity": False, "duration": False},
    "quantity": {"quantity": True, "duration": False},
    "duration": {"quantity": False, "duration": True},
    "both": {"quantity": True, "duration": True},
}

SUMMARY_METRICS = [
    "service_level_percent",
    "average_lead_time_days",
    "total_cost",
    "total_recognized_profit",
    "lost_revenue_due_to_late_orders",
    "total_emissions",
    "average_waste",
]


def add_quantity_noise(orders, cv: float, seed: int):
    """Units of each order x (1 + e), e ~ N(0, cv), at least 1 unit."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, cv, size=len(orders))

    for order, e in zip(orders, noise):
        order.production_units = max(
            1, int(round(order.production_units * (1.0 + e)))
        )

    return orders


def run_one(
    case_config: dict,
    process_config: dict,
    orders_path: Path,
    demand_multiplier: float,
    quantity_cv: float,
    duration_cv: float,
    seed: int,
    prototyping_type: str | None = None,
):
    orders = load_orders_from_json(str(orders_path))
    orders = apply_demand_multiplier(orders, demand_multiplier)

    # Orders are processed in a fixed order, so the noise is reproducible
    orders.sort(key=lambda order: order.init_date)

    if quantity_cv > 0:
        orders = add_quantity_noise(orders, quantity_cv, seed)

    set_duration_noise(duration_cv, seed=seed + 10_000)

    config = deepcopy(process_config)

    prototyping_type = prototyping_type or case_config["simulation"]["prototyping_type"]
    simulation_until = case_config["simulation"]["until"]

    env = simpy.Environment()
    scheduler = Scheduler(env)
    resources = Resources(env, config)

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

    set_duration_noise(0.0)

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

    return completed_orders, config, first_date


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (scenario, variant), group in df.groupby(
        ["scenario", "variant"], sort=False
    ):
        row = {"scenario": scenario, "variant": variant, "runs": len(group)}

        for metric in SUMMARY_METRICS:
            values = group[metric].astype(float)
            row[f"{metric}_mean"] = values.mean()
            row[f"{metric}_std"] = values.std(ddof=1) if len(values) > 1 else 0.0
            row[f"{metric}_p5"] = values.quantile(0.05)
            row[f"{metric}_p95"] = values.quantile(0.95)

        rows.append(row)

    return pd.DataFrame(rows)


PAIRED_METRICS = [
    "total_cost",
    "total_recognized_profit",
    "average_waste",
    "total_emissions",
    "service_level_percent",
]


def paired_prototyping(df: pd.DataFrame) -> pd.DataFrame:
    """Paired difference DIGITAL - PHYSICAL per seed and variant."""
    phys = df[df["scenario"] == "prototyping_PHYSICAL"]
    digi = df[df["scenario"] == "prototyping_DIGITAL"]

    rows = []

    for variant in VARIANTS:
        a = phys[phys["variant"] == variant].set_index("seed")
        b = digi[digi["variant"] == variant].set_index("seed")
        seeds = a.index.intersection(b.index)

        row = {"variant": variant, "runs": len(seeds)}

        for metric in PAIRED_METRICS:
            diff = (b.loc[seeds, metric] - a.loc[seeds, metric]).astype(float)
            row[f"{metric}_diff_mean"] = diff.mean()
            row[f"{metric}_diff_p5"] = diff.quantile(0.05)
            row[f"{metric}_diff_p95"] = diff.quantile(0.95)

        # share of runs in which digital is better than physical
        row["share_digital_lower_cost"] = float(
            (b.loc[seeds, "total_cost"] < a.loc[seeds, "total_cost"]).mean()
        )
        row["share_digital_higher_profit"] = float(
            (
                b.loc[seeds, "total_recognized_profit"]
                > a.loc[seeds, "total_recognized_profit"]
            ).mean()
        )
        row["share_digital_lower_waste"] = float(
            (b.loc[seeds, "average_waste"] < a.loc[seeds, "average_waste"]).mean()
        )

        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    project_root = scenario_dir.parents[2]

    scenarios_config = load_json(scenario_dir / "scenarios_config.json")
    robustness = scenarios_config["robustness"]
    paths = scenarios_config["paths"]

    case_config = load_json(project_root / paths["case_config"])
    case_data_dir = project_root / paths["case_data_dir"]

    orders_path = case_data_dir / case_config["input_files"]["orders"]
    process_config = load_config(
        str(case_data_dir / case_config["input_files"]["process_config"])
    )

    output_dir = project_root / "results" / "experiments" / "mto_case"
    output_dir.mkdir(parents=True, exist_ok=True)

    replications = int(robustness["replications"])
    rows = []

    experiments = [
        (build_scenario_name(m), m, None) for m in robustness["multipliers"]
    ]
    experiments += [
        (f"prototyping_{ptype}", 1.0, ptype)
        for ptype in robustness.get("prototyping_types", [])
    ]

    for scenario_name, multiplier, ptype in experiments:
        for variant, flags in VARIANTS.items():
            n_runs = 1 if variant == "deterministic" else replications

            print(f"Running {scenario_name} / {variant} ({n_runs} runs)...")

            for seed in range(n_runs):
                # The simulation prints a lot: silence it
                with contextlib.redirect_stdout(io.StringIO()):
                    completed_orders, config, first_date = run_one(
                        case_config=case_config,
                        process_config=process_config,
                        orders_path=orders_path,
                        demand_multiplier=multiplier,
                        quantity_cv=(
                            float(robustness["quantity_cv"])
                            if flags["quantity"] else 0.0
                        ),
                        duration_cv=(
                            float(robustness["duration_cv"])
                            if flags["duration"] else 0.0
                        ),
                        seed=seed,
                        prototyping_type=ptype,
                    )

                    kpis = extract_kpis(
                        scenario_name=scenario_name,
                        demand_multiplier=multiplier,
                        completed_orders=completed_orders,
                        process_config=config,
                        first_date=first_date,
                    )

                kpis["scenario"] = scenario_name
                kpis["variant"] = variant
                kpis["seed"] = seed
                rows.append(kpis)

    df = pd.DataFrame(rows)
    df.to_csv(output_dir / robustness["output_file"], index=False)

    df_summary = summarise(df)
    df_summary.to_csv(output_dir / robustness["summary_file"], index=False)

    if robustness.get("prototyping_types"):
        paired = paired_prototyping(df)
        paired.to_csv(
            output_dir / "results_robustness_prototyping_paired.csv",
            index=False,
        )

    print(f"Results saved in: {output_dir / robustness['output_file']}")
    print(f"Summary saved in: {output_dir / robustness['summary_file']}")


if __name__ == "__main__":
    main()
