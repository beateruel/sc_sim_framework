# core/mts/analytics/kpis/throughput.py

from __future__ import annotations

import pandas as pd


def compute_mts_throughput(
    production_df: pd.DataFrame,
) -> pd.DataFrame:
    if production_df.empty:
        return pd.DataFrame(columns=["week", "weekly_throughput"])

    throughput = (
        production_df
        .groupby("week", as_index=False)["produced_quantity"]
        .sum()
        .rename(columns={"produced_quantity": "weekly_throughput"})
    )

    return throughput


def compute_total_throughput(
    production_df: pd.DataFrame,
) -> pd.DataFrame:
    total_produced = (
        production_df["produced_quantity"].sum()
        if not production_df.empty
        else 0.0
    )

    return pd.DataFrame(
        [{"total_throughput": total_produced}]
    )


def compute_production_plan_fulfillment(
    production_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Measures how much of the planned production was actually produced.

    This is not capacity utilization.
    """

    if production_df.empty:
        return pd.DataFrame(
            [
                {
                    "total_planned_quantity": 0.0,
                    "total_produced_quantity": 0.0,
                    "production_plan_fulfillment": 0.0,
                    "production_plan_fulfillment_percent": 0.0,
                }
            ]
        )

    total_planned = production_df["planned_quantity"].sum()
    total_produced = production_df["produced_quantity"].sum()

    fulfillment = (
        total_produced / total_planned
        if total_planned > 0
        else 0.0
    )

    return pd.DataFrame(
        [
            {
                "total_planned_quantity": total_planned,
                "total_produced_quantity": total_produced,
                "production_plan_fulfillment": fulfillment,
                "production_plan_fulfillment_percent": fulfillment * 100,
            }
        ]
    )


def compute_capacity_utilization(
    production_df: pd.DataFrame,
    weekly_capacity_hours: float,
) -> pd.DataFrame:
    """
    Computes weekly capacity utilization.

    Capacity utilization =
        production_time_hours / weekly_capacity_hours

    Values can exceed 1.0 if the production plan exceeds available capacity.
    """

    if production_df.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "production_time_hours",
                "weekly_capacity_hours",
                "capacity_utilization",
                "capacity_utilization_percent",
            ]
        )

    if weekly_capacity_hours <= 0:
        raise ValueError("weekly_capacity_hours must be greater than zero.")

    df = (
        production_df
        .groupby("week", as_index=False)["production_time_hours"]
        .sum()
    )

    df["weekly_capacity_hours"] = weekly_capacity_hours
    df["capacity_utilization"] = (
        df["production_time_hours"] / df["weekly_capacity_hours"]
    )
    df["capacity_utilization_percent"] = (
        df["capacity_utilization"] * 100
    )

    return df


def compute_capacity_utilization_summary(
    production_df: pd.DataFrame,
    weekly_capacity_hours: float,
) -> pd.DataFrame:
    """
    Computes average and maximum capacity utilization across weeks.
    """

    df = compute_capacity_utilization(
        production_df=production_df,
        weekly_capacity_hours=weekly_capacity_hours,
    )

    if df.empty:
        return pd.DataFrame(
            [
                {
                    "capacity_utilization_mean": 0.0,
                    "capacity_utilization_mean_percent": 0.0,
                    "capacity_utilization_max": 0.0,
                    "capacity_utilization_max_percent": 0.0,
                }
            ]
        )

    mean_utilization = df["capacity_utilization"].mean()
    max_utilization = df["capacity_utilization"].max()

    return pd.DataFrame(
        [
            {
                "capacity_utilization_mean": mean_utilization,
                "capacity_utilization_mean_percent": mean_utilization * 100,
                "capacity_utilization_max": max_utilization,
                "capacity_utilization_max_percent": max_utilization * 100,
            }
        ]
    )


def compute_production_lead_time(
    production_df: pd.DataFrame,
) -> pd.DataFrame:
    if production_df.empty:
        return pd.DataFrame(
            [{"average_production_time_hours": 0.0}]
        )

    produced_df = production_df[
        production_df["produced_quantity"] > 0
    ].copy()

    if produced_df.empty:
        avg_production_time = 0.0
    else:
        avg_production_time = produced_df["production_time_hours"].mean()

    return pd.DataFrame(
        [{"average_production_time_hours": avg_production_time}]
    )