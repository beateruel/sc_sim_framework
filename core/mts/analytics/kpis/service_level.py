# core/mts/analytics/kpis/service_level.py

from __future__ import annotations

import pandas as pd


def compute_mts_otif(
    distribution_df: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    """
    Computes OTIF (On Time In Full) for MTS.

    Assumptions:
    - Demand is weekly.
    - No backlog is allowed.
    - Deliveries recorded in the same week are considered on-time.
    - OTIF = 1 only if the full requested quantity is shipped.
    """

    if distribution_df.empty:
        return pd.DataFrame(), 0.0

    df = distribution_df.copy()

    df["otif"] = (
        df["shipped_quantity"].round(6)
        >= df["requested_quantity"].round(6)
    ).astype(int)

    service_level = float(df["otif"].mean())

    otif_detail = df[
        [
            "week",
            "product_id",
            "product_name",
            "requested_quantity",
            "shipped_quantity",
            "unfilled_quantity",
            "otif",
        ]
    ].copy()

    return otif_detail, service_level


def compute_mts_fill_rate(
    distribution_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes fill rate by product-week.

    Fill Rate =
        shipped_quantity / requested_quantity
    """

    if distribution_df.empty:
        return pd.DataFrame()

    df = distribution_df.copy()

    df["fill_rate"] = (
        df["shipped_quantity"]
        / df["requested_quantity"]
    ).fillna(0.0)

    return df[
        [
            "week",
            "product_id",
            "product_name",
            "requested_quantity",
            "shipped_quantity",
            "unfilled_quantity",
            "fill_rate",
        ]
    ]


def compute_mts_fill_rate_summary(
    distribution_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes global fill rate for the entire simulation.
    """

    if distribution_df.empty:
        return pd.DataFrame(
            [
                {
                    "requested_quantity": 0.0,
                    "shipped_quantity": 0.0,
                    "unfilled_quantity": 0.0,
                    "fill_rate": 0.0,
                    "fill_rate_percent": 0.0,
                }
            ]
        )

    total_requested = distribution_df["requested_quantity"].sum()
    total_shipped = distribution_df["shipped_quantity"].sum()

    fill_rate = (
        total_shipped / total_requested
        if total_requested > 0
        else 0.0
    )

    return pd.DataFrame(
        [
            {
                "requested_quantity": total_requested,
                "shipped_quantity": total_shipped,
                "unfilled_quantity": total_requested - total_shipped,
                "fill_rate": fill_rate,
                "fill_rate_percent": fill_rate * 100,
            }
        ]
    )


def compute_mts_stockout_rate(
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes stockout rate across simulation weeks.
    """

    if inventory_df.empty:
        return pd.DataFrame(
            [
                {
                    "stockout_rate": 0.0,
                    "stockout_rate_percent": 0.0,
                    "stockout_weeks": 0,
                    "total_weeks": 0,
                }
            ]
        )

    stockout_rate = inventory_df["stockout"].mean()

    return pd.DataFrame(
        [
            {
                "stockout_rate": stockout_rate,
                "stockout_rate_percent": stockout_rate * 100,
                "stockout_weeks": int(
                    inventory_df["stockout"].sum()
                ),
                "total_weeks": len(inventory_df),
            }
        ]
    )