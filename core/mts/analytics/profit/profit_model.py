# core/mts/analytics/profit/profit_model.py

from __future__ import annotations

import pandas as pd


def compute_mts_profit(
    distribution_df: pd.DataFrame,
    cost_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes MTS profit indicators.
    """

    total_income = (
        distribution_df["income"].sum()
        if "income" in distribution_df.columns
        else 0
    )

    total_cost = (
        cost_df["total_cost"].iloc[0]
        if len(cost_df) > 0
        else 0
    )

    total_profit = total_income - total_cost

    profit_margin = (
        total_profit / total_income
        if total_income > 0
        else 0
    )

    return pd.DataFrame(
        [
            {
                "total_income": total_income,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "profit_margin": profit_margin,
            }
        ]
    )