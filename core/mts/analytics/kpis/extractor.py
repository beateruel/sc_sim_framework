# core/mts/analytics/kpis/extractor.py

from __future__ import annotations

import pandas as pd


def extract_inventory_metrics(
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract inventory-related operational metrics.
    """

    metrics = pd.DataFrame()

    metrics["week"] = inventory_df["week"]

    metrics["total_raw_material_oh"] = inventory_df[
        "total_raw_material_oh"
    ]

    metrics["total_raw_material_it"] = inventory_df[
        "total_raw_material_it"
    ]

    metrics["total_finished_goods"] = inventory_df[
        "total_finished_goods"
    ]

    metrics["stockout"] = inventory_df["stockout"]

    return metrics


def extract_distribution_metrics(
    distribution_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract delivery/service operational metrics.
    """

    metrics = distribution_df.copy()

    metrics["fill_rate"] = (
        metrics["shipped_quantity"]
        / metrics["requested_quantity"]
    ).fillna(0)

    return metrics


def extract_production_metrics(
    production_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract production operational metrics.
    """

    metrics = production_df.copy()

    metrics["production_efficiency"] = (
        metrics["produced_quantity"]
        / metrics["planned_quantity"]
    ).fillna(0)

    return metrics


def extract_purchase_metrics(
    purchase_orders_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract sourcing operational metrics.
    """

    metrics = purchase_orders_df.copy()

    if "purchase_cost" in metrics.columns:
        metrics["unit_purchase_cost"] = (
            metrics["purchase_cost"]
            / metrics["quantity"]
        ).fillna(0)

    return metrics