# core/mts/analytics/cost/cost_model.py

from __future__ import annotations

import pandas as pd


def compute_mts_costs(
    purchase_orders_df: pd.DataFrame,
    production_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    holding_rate: float = 0.2,
) -> pd.DataFrame:
    """
    Computes global MTS cost structure.
    """

    purchase_cost = (
        purchase_orders_df["purchase_cost"].sum()
        if "purchase_cost" in purchase_orders_df.columns
        else 0
    )

    ordering_cost = (
        purchase_orders_df["ordering_cost"].sum()
        if "ordering_cost" in purchase_orders_df.columns
        else 0
    )

    production_cost = (
        production_df["production_time_hours"].sum()
        if "production_time_hours" in production_df.columns
        else 0
    )

    distribution_cost = (
        distribution_df["distribution_time_hours"].sum()
        if "distribution_time_hours" in distribution_df.columns
        else 0
    )

    average_inventory = inventory_df[
        "total_raw_material_oh"
    ].mean()

    holding_cost = average_inventory * holding_rate

    total_cost = (
        purchase_cost
        + ordering_cost
        + production_cost
        + distribution_cost
        + holding_cost
    )

    return pd.DataFrame(
        [
            {
                "purchase_cost": purchase_cost,
                "ordering_cost": ordering_cost,
                "production_cost": production_cost,
                "distribution_cost": distribution_cost,
                "holding_cost": holding_cost,
                "total_cost": total_cost,
            }
        ]
    )