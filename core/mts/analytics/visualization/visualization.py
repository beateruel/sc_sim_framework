from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def plot_mts_raw_material_inventory(
    inventory_df: pd.DataFrame,
    material_id: str,
    material_label: str,
    output_path: Optional[str | Path] = None,
    show: bool = False,
) -> None:

    material_id = str(material_id)

    oh_col = f"raw_material_oh_{material_id}"
    it_col = f"raw_material_it_{material_id}"

    _validate_columns(inventory_df, ["week", oh_col, it_col])

    fig, ax = plt.subplots(figsize=(15, 5))

    ax.plot(
        inventory_df["week"],
        inventory_df[oh_col],
        label=f"OHI - {material_label}",
    )

    ax.plot(
        inventory_df["week"],
        inventory_df[it_col],
        label=f"ITI - {material_label}",
    )

    ax.set_xlabel("Weeks", fontsize=14, fontweight="bold")
    ax.set_ylabel("Inventory (kg)")
    ax.set_title(f"Raw material inventory - {material_label}")

    ax.set_xlim(
        inventory_df["week"].min(),
        inventory_df["week"].max(),
    )

    ax.set_xticks(inventory_df["week"].astype(int).tolist())

    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    _save_or_show(fig, output_path, show)


def plot_mts_inventory_individual(
    inventory_df: pd.DataFrame,
    weekly_demand: pd.DataFrame,
    material_id: str,
    material_label: str,
    product_ids: list[str],
    product_labels: dict[str, str],
    output_path: Optional[str | Path] = None,
    show: bool = False,
) -> None:

    material_id = str(material_id)

    oh_col = f"raw_material_oh_{material_id}"
    it_col = f"raw_material_it_{material_id}"

    required_columns = ["week", oh_col, it_col]

    for product_id in product_ids:
        required_columns.append(f"finished_goods_{product_id}")

    _validate_columns(inventory_df, required_columns)

    demand_series = _build_total_weekly_demand_series(
        weekly_demand
    )

    n_subplots = 2 + len(product_ids) + 1

    fig, axes = plt.subplots(
        n_subplots,
        1,
        figsize=(12, 2.5 * n_subplots),
        constrained_layout=True,
    )

    axes[0].plot(
        inventory_df["week"],
        inventory_df[oh_col],
    )

    axes[0].set_title(
        f"OHI - {material_label} (kg)"
    )

    axes[0].set_ylim(bottom=0)

    axes[1].plot(
        inventory_df["week"],
        inventory_df[it_col],
    )

    axes[1].set_title(
        f"ITI - {material_label} (kg)"
    )

    axes[1].set_ylim(bottom=0)

    for idx, product_id in enumerate(product_ids):

        fg_col = f"finished_goods_{product_id}"

        product_label = product_labels.get(
            product_id,
            product_id,
        )

        axes[idx + 2].plot(
            inventory_df["week"],
            inventory_df[fg_col],
        )

        axes[idx + 2].set_title(
            f"FI {product_label} (units)"
        )

        axes[idx + 2].set_ylim(bottom=0)

    axes[-1].plot(
        demand_series.index,
        demand_series.values,
    )

    axes[-1].set_title(
        "Demand (units)"
    )

    axes[-1].set_ylim(bottom=0)

    for axis in axes:
        axis.grid(True, alpha=0.3)

    _save_or_show(fig, output_path, show)


def plot_mts_finished_goods(
    inventory_df: pd.DataFrame,
    product_ids: list[str],
    product_labels: dict[str, str],
    output_path: Optional[str | Path] = None,
    show: bool = False,
) -> None:

    required_columns = ["week"]

    for product_id in product_ids:
        required_columns.append(
            f"finished_goods_{product_id}"
        )

    _validate_columns(
        inventory_df,
        required_columns,
    )

    fig, ax = plt.subplots(figsize=(15, 5))

    for product_id in product_ids:

        fg_col = f"finished_goods_{product_id}"

        product_label = product_labels.get(
            product_id,
            product_id,
        )

        ax.plot(
            inventory_df["week"],
            inventory_df[fg_col],
            label=f"FI {product_label}",
        )

    ax.set_xlabel(
        "Weeks",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_ylabel(
        "Finished goods inventory",
    )

    ax.set_title(
        "Finished goods inventory",
    )

    ax.set_xlim(
        inventory_df["week"].min(),
        inventory_df["week"].max(),
    )

    ax.set_xticks(
        inventory_df["week"].astype(int).tolist()
    )

    ax.legend()

    ax.grid(True, alpha=0.3)

    ax.set_ylim(bottom=0)

    _save_or_show(fig, output_path, show)


def plot_mts_demand(
    weekly_demand: pd.DataFrame,
    output_path: Optional[str | Path] = None,
    show: bool = False,
) -> None:

    demand_series = _build_total_weekly_demand_series(
        weekly_demand
    )

    fig, ax = plt.subplots(figsize=(15, 5))

    ax.plot(
        demand_series.index,
        demand_series.values,
    )

    ax.set_xlabel(
        "Weeks",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_ylabel(
        "Demand (units)",
    )

    ax.set_title(
        "Weekly demand",
    )

    ax.set_xlim(
        demand_series.index.min(),
        demand_series.index.max(),
    )

    ax.set_xticks(
        demand_series.index.astype(int).tolist()
    )

    ax.grid(True, alpha=0.3)

    ax.set_ylim(bottom=0)

    _save_or_show(fig, output_path, show)


def _build_total_weekly_demand_series(
    weekly_demand: pd.DataFrame,
) -> pd.Series:

    _validate_columns(
        weekly_demand,
        ["week", "quantity_units"],
    )

    return (
        weekly_demand
        .groupby("week")["quantity_units"]
        .sum()
        .sort_index()
    )


def _validate_columns(
    df: pd.DataFrame,
    required_columns: list[str],
) -> None:

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )


def _save_or_show(
    fig: plt.Figure,
    output_path: Optional[str | Path],
    show: bool,
) -> None:

    if output_path is not None:

        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fig.savefig(
            output_path,
            dpi=150,
            bbox_inches="tight",
        )

    if show:
        plt.show()

    plt.close(fig)