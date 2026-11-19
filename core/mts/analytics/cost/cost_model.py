# core/mts/analytics/cost/cost_model.py

from __future__ import annotations

import pandas as pd


def compute_mts_costs(
    purchase_orders_df: pd.DataFrame,
    production_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    holding_rate: float = 0.2,
    labour_cost_per_hour: float = 17.0,
    client_distribution_cost: float = 100.0,
) -> pd.DataFrame:
    purchase_cost = (
        purchase_orders_df["purchase_cost"].sum()
        if "purchase_cost" in purchase_orders_df.columns else 0
    )
    ordering_cost = (
        purchase_orders_df["ordering_cost"].sum()
        if "ordering_cost" in purchase_orders_df.columns else 0
    )

    # Labour cost: only hours of production actually carried out
    if {"production_time_hours", "status"}.issubset(production_df.columns):
        production_hours = production_df.loc[
            production_df["status"] == "produced", "production_time_hours"
        ].sum()
    else:
        production_hours = 0

    production_cost = production_hours * labour_cost_per_hour

    # Fixed cost per week with client deliveries (as in the simulator)
    delivery_weeks = (
        distribution_df["week"].nunique()
        if "week" in distribution_df.columns else 0
    )
    distribution_cost = delivery_weeks * client_distribution_cost

    # Reported separately, not included in total_cost (as in the simulator)
    average_inventory = inventory_df["total_raw_material_oh"].mean()
    holding_cost = average_inventory * holding_rate

    total_cost = (
        purchase_cost + ordering_cost + production_cost + distribution_cost
    )

    return pd.DataFrame([{
        "purchase_cost": purchase_cost,
        "ordering_cost": ordering_cost,
        "production_cost": production_cost,
        "distribution_cost": distribution_cost,
        "total_cost": total_cost,
        "holding_cost_memo": holding_cost,
    }])

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