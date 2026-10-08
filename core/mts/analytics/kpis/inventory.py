# core/mts/analytics/kpis/inventory.py

from __future__ import annotations

import pandas as pd


def compute_average_inventory(
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes average inventory levels by inventory buffer type.

    The function separates:
    - raw material on-hand inventory,
    - raw material in-transit inventory,
    - finished-goods inventory.

    This avoids mixing structurally different inventory buffers
    into a single aggregated indicator.
    """

    average_raw_material_oh = inventory_df[
        "total_raw_material_oh"
    ].mean()

    average_raw_material_it = inventory_df[
        "total_raw_material_it"
    ].mean()

    average_finished_goods = inventory_df[
        "total_finished_goods"
    ].mean()

    average_total_inventory = (
        average_raw_material_oh
        + average_raw_material_it
        + average_finished_goods
    )

    return pd.DataFrame(
        [
            {
                "average_raw_material_oh": average_raw_material_oh,
                "average_raw_material_it": average_raw_material_it,
                "average_finished_goods": average_finished_goods,
                "average_total_inventory": average_total_inventory,
            }
        ]
    )


def compute_inventory_turnover(
    inventory_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes inventory turnover ratio.

    turnover = shipped units / average finished goods inventory
    """

    total_shipped = distribution_df["shipped_quantity"].sum()

    average_fg_inventory = inventory_df[
        "total_finished_goods"
    ].mean()

    turnover = (
        total_shipped / average_fg_inventory
        if average_fg_inventory > 0
        else 0
    )

    return pd.DataFrame(
        [
            {
                "total_shipped_quantity": total_shipped,
                "average_finished_goods_inventory": average_fg_inventory,
                "inventory_turnover": turnover,
            }
        ]
    )


def compute_inventory_variability(
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes inventory variability indicators.
    """

    return pd.DataFrame(
        [
            {
                "raw_material_oh_std": inventory_df[
                    "total_raw_material_oh"
                ].std(),

                "raw_material_it_std": inventory_df[
                    "total_raw_material_it"
                ].std(),

                "finished_goods_std": inventory_df[
                    "total_finished_goods"
                ].std(),
            }
        ]
    )


def compute_inventory_peaks(
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes inventory peak levels.
    """

    return pd.DataFrame(
        [
            {
                "max_raw_material_oh": inventory_df[
                    "total_raw_material_oh"
                ].max(),

                "max_raw_material_it": inventory_df[
                    "total_raw_material_it"
                ].max(),

                "max_finished_goods": inventory_df[
                    "total_finished_goods"
                ].max(),
            }
        ]
    )