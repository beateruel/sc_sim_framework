"""
Robustness test of the MTS case under stochastic demand and lead time.

For each scenario (baseline and supply interruption) the model is run with:
    deterministic : no randomness (reference, one run)
    demand        : actual weekly demand = planned demand x (1 + e),
                    e ~ N(0, demand_cv); planning uses the deterministic forecast
    lead_time     : supplier lead time of each purchase order + U{-j..+j} weeks
    both          : demand and lead time randomness together

Each stochastic variant is replicated with seeds 0..R-1. The same seed is used
in every variant and scenario (common random numbers), so that differences
between variants are not caused by sampling noise.

Outputs (results/experiments/mts_case/):
    results_robustness.csv          one row per run
    results_robustness_summary.csv  mean, std, P5 and P95 per scenario/variant
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from core.mts.data.loaders import (
    load_products_bom,
    load_suppliers,
    load_weekly_demand_mts,
)
from core.mts.simulation.runner import MTSSimulationRunner

from cases.mts_case.scenarios.run_supply_interruption import (
    build_material_prices,
    build_mts_config,
    extract_kpis,
    load_json,
)

VARIANTS = {
    "deterministic": {"demand": False, "lead_time": False},
    "demand": {"demand": True, "lead_time": False},
    "lead_time": {"demand": False, "lead_time": True},
    "both": {"demand": True, "lead_time": True},
}

SUMMARY_METRICS = [
    "service_level_percent",
    "production_plan_fulfillment_percent",
    "average_total_inventory",
    "summary_total_profit",
    "total_emissions",
]


def add_demand_noise(
    planned: pd.DataFrame,
    cv: float,
    seed: int,
) -> pd.DataFrame:
    """Actual demand = planned demand x (1 + e), e ~ N(0, cv), floored at 0."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, cv, size=len(planned))

    actual = planned.copy()
    actual["quantity_units"] = np.maximum(
        0,
        np.round(planned["quantity_units"].to_numpy() * (1.0 + noise)),
    ).astype(int)

    return actual


def run_one(
    case_config: dict,
    case_data_dir: Path,
    scenario: dict,
    use_demand_noise: bool,
    use_lead_time_noise: bool,
    demand_cv: float,
    lead_time_jitter_weeks: int,
    seed: int,
) -> tuple[dict, dict]:
    config = deepcopy(case_config)
    config["simulation"]["demand_variation"] = 0.0
    config["simulation"]["shortage_start_week"] = scenario["start_week"]
    config["simulation"]["shortage_end_week"] = scenario["end_week"]

    planned_demand = load_weekly_demand_mts(
        case_data_dir / config["input_files"]["demand"],
        variation=0.0,
    )

    actual_demand = (
        add_demand_noise(planned_demand, demand_cv, seed)
        if use_demand_noise
        else planned_demand
    )

    mts_config = replace(
        build_mts_config(config),
        lead_time_jitter_weeks=lead_time_jitter_weeks if use_lead_time_noise else 0,
        random_seed=seed + 10_000,
    )

    runner = MTSSimulationRunner(
        weekly_demand=actual_demand,
        planning_demand=planned_demand,
        products_bom=load_products_bom(
            case_data_dir / config["input_files"]["bom"],
        ),
        suppliers=load_suppliers(
            case_data_dir / config["input_files"]["suppliers"],
        ),
        material_prices=build_material_prices(config),
        config=mts_config,
        shortage_start_week=scenario["start_week"],
        shortage_end_week=scenario["end_week"],
        initial_raw_material_inventory=config["initial_inventory"]["raw_material"],
        initial_finished_goods_inventory=config["initial_inventory"][
            "finished_goods"
        ],
    )

    summary = runner.run()
    results = runner.get_results()

    return summary, results


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (scenario, variant), group in df.groupby(
        ["scenario", "variant"], sort=False
    ):
        row = {
            "scenario": scenario,
            "variant": variant,
            "runs": len(group),
        }

        for metric in SUMMARY_METRICS:
            values = group[metric].astype(float)
            row[f"{metric}_mean"] = values.mean()
            row[f"{metric}_std"] = values.std(ddof=1) if len(values) > 1 else 0.0
            row[f"{metric}_p5"] = values.quantile(0.05)
            row[f"{metric}_p95"] = values.quantile(0.95)

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

    output_dir = project_root / "results" / "experiments" / "mts_case"
    output_dir.mkdir(parents=True, exist_ok=True)

    replications = int(robustness["replications"])
    rows = []

    for scenario in robustness["scenarios"]:
        for variant, flags in VARIANTS.items():
            n_runs = 1 if variant == "deterministic" else replications

            print(f"Running {scenario['name']} / {variant} ({n_runs} runs)...")

            for seed in range(n_runs):
                summary, results = run_one(
                    case_config=case_config,
                    case_data_dir=case_data_dir,
                    scenario=scenario,
                    use_demand_noise=flags["demand"],
                    use_lead_time_noise=flags["lead_time"],
                    demand_cv=float(robustness["demand_cv"]),
                    lead_time_jitter_weeks=int(robustness["lead_time_jitter_weeks"]),
                    seed=seed,
                )

                kpis = extract_kpis(
                    scenario_name=scenario["name"],
                    shortage_start_week=scenario["start_week"],
                    shortage_end_week=scenario["end_week"],
                    summary=summary,
                    results=results,
                    case_config=case_config,
                    case_data_dir=case_data_dir,
                )

                kpis["scenario"] = scenario["name"]
                kpis["variant"] = variant
                kpis["seed"] = seed
                rows.append(kpis)

    df = pd.DataFrame(rows)
    df.to_csv(output_dir / robustness["output_file"], index=False)

    df_summary = summarise(df)
    df_summary.to_csv(output_dir / robustness["summary_file"], index=False)

    print(f"Results saved in: {output_dir / robustness['output_file']}")
    print(f"Summary saved in: {output_dir / robustness['summary_file']}")


if __name__ == "__main__":
    main()
