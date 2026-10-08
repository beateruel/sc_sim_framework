"""
Publication-oriented reporting figures for the MTS case.

Input CSV files:
    results/experiments/mts_case/results_demand_variation.csv
    results/experiments/mts_case/results_shortage.csv
    results/experiments/mts_case/results_lead_time_shock.csv

Output figures:
    results/experiments/mts_case/visualization/
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

def find_project_root() -> Path:
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "README.md").exists() and (parent / "requirements.txt").exists():
            return parent

    raise RuntimeError(
        "Project root not found. README.md and requirements.txt are required."
    )


PROJECT_ROOT = find_project_root()
RESULTS_DIR = PROJECT_ROOT / "results"
MTS_CASE_DIR = RESULTS_DIR / "experiments" / "mts_case"
OUTPUT_DIR = MTS_CASE_DIR / "visualization"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def read_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

    # Works for comma CSV and semicolon CSV with comma decimals.
    try:
        df = pd.read_csv(path)
        if len(df.columns) == 1:
            df = pd.read_csv(path, sep=";", decimal=",")
    except Exception:
        df = pd.read_csv(path, sep=";", decimal=",")

    return df


def save_figure(fig, filename: str) -> None:
    png_path = OUTPUT_DIR / f"{filename}.png"
    pdf_path = OUTPUT_DIR / f"{filename}.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {png_path}")
    print(f"Saved: {pdf_path}")


def apply_axis_style(ax) -> None:
    ax.grid(True, linewidth=0.5, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def format_thousands_axis(ax) -> None:
    ax.get_yaxis().set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{int(x):,}")
    )

def set_auto_ylim_with_margin(ax, values, margin_ratio=0.25):
    """
    Set y-axis limits with an automatic margin around the data.
    Useful when values are very close but starting from zero hides variation.
    """

    values = pd.Series(values).dropna()

    ymin = values.min()
    ymax = values.max()

    if ymin == ymax:
        margin = abs(ymax) * margin_ratio if ymax != 0 else 1
    else:
        margin = (ymax - ymin) * margin_ratio

    ax.set_ylim(
        ymin - margin,
        ymax + margin,
    )


def demand_labels(values) -> list[str]:
    labels = []

    for value in values:
        value = int(round(float(value)))

        if value == 0:
            labels.append("Baseline")
        elif value > 0:
            labels.append(f"+{value}%")
        else:
            labels.append(f"{value}%")

    return labels


def validate_columns(df: pd.DataFrame, required_columns: list[str], figure_name: str) -> None:
    missing = [column for column in required_columns if column not in df.columns]

    if missing:
        raise KeyError(
            f"{figure_name} cannot be generated. Missing columns: {missing}. "
            "Regenerate the scenario CSVs after updating the KPI extraction code."
        )


def plot_inventory_buffers(ax, x, df: pd.DataFrame) -> None:
    """
    Raw values (used in Figure 5: demand variation).
    """

    ax.plot(
        x,
        df["average_raw_material_oh"],
        marker="o",
        color="tab:blue",
        label="Raw material OH (kg)",
    )

    ax.set_title("(b) Raw-material and finished-goods inventories")
    ax.set_ylabel("Raw material OH (kg)")
    format_thousands_axis(ax)

    ax_fg = ax.twinx()

    ax_fg.plot(
        x,
        df["average_finished_goods"],
        marker="s",
         color="tab:orange",
        label="Finished goods (units)",
    )

    ax_fg.set_ylabel("Finished goods (units)")
    format_thousands_axis(ax_fg)

    lines_1, labels_1 = ax.get_legend_handles_labels()
    lines_2, labels_2 = ax_fg.get_legend_handles_labels()

    ax.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        frameon=False,
        loc="lower left",
    )

    ax_fg.spines["top"].set_visible(False)
    ax_fg.grid(False)


def plot_inventory_buffers_normalized(ax, x, df: pd.DataFrame) -> None:
    """
    Normalized inventory indices (base scenario = 100).
    Used in Figures 6 and 7.
    """

    rm_base = df["average_raw_material_oh"].iloc[0]
    fg_base = df["average_finished_goods"].iloc[0]

    rm_index = 100 * df["average_raw_material_oh"] / rm_base
    fg_index = 100 * df["average_finished_goods"] / fg_base

    ax.plot(
        x,
        rm_index,
        marker="o",
        color="tab:blue",
        label="Raw material OH",
    )

    ax.plot(
        x,
        fg_index,
        marker="s",
        color="tab:orange",
        label="Finished goods",
    )

    ax.set_title("(b) Inventory index")
    ax.set_ylabel("Inventory index (base = 100)")
    ax.legend(frameon=False, loc="best")

    ymin = min(rm_index.min(), fg_index.min())
    ymax = max(rm_index.max(), fg_index.max())

    margin = (ymax - ymin) * 0.20

    ax.set_ylim(
        ymin - margin,
        ymax + margin,
    )


def style_all_axes(axs, x_label: str, rotate_x: bool = False) -> None:
    for ax in axs.flat:
        ax.set_xlabel(x_label)
        apply_axis_style(ax)

        if rotate_x:
            ax.tick_params(axis="x", rotation=30)


# ---------------------------------------------------------------------
# Figure 5 — Demand variation
# ---------------------------------------------------------------------

def plot_demand_variation(
    csv_path: Path = MTS_CASE_DIR / "results_demand_variation.csv",
) -> None:
    df = read_results(csv_path)
    df = df.sort_values("demand_variation_percent")

    required_columns = [
        "demand_variation_percent",
        "service_level_percent",
        "average_raw_material_oh",
        "average_finished_goods",
        "production_plan_fulfillment_percent",
        "summary_total_profit",
    ]
    validate_columns(df, required_columns, "Demand variation figure")

    x_labels = demand_labels(df["demand_variation_percent"])

    fig, axs = plt.subplots(2, 2, figsize=(9, 6))

    # (a) Service level
    axs[0, 0].plot(
        x_labels,
        df["service_level_percent"],
        marker="o",
    )
    axs[0, 0].set_title("(a) Service level")
    axs[0, 0].set_ylabel("Service level (%)")
    axs[0, 0].set_ylim(0, 110)

    # (b) Inventory buffers
    plot_inventory_buffers(
        ax=axs[0, 1],
        x=x_labels,
        df=df,
    )

    # (c) Production fulfilment
    axs[1, 0].plot(
        x_labels,
        df["production_plan_fulfillment_percent"],
        marker="o",
    )
    axs[1, 0].set_title("(c) Production fulfilment")
    axs[1, 0].set_ylabel("Production fulfilment (%)")
    axs[1, 0].set_ylim(0, 110)

    # (d) Profit
    axs[1, 1].plot(
        x_labels,
        df["summary_total_profit"],
        marker="o",
    )
    axs[1, 1].set_title("(d) Profit")
   
    format_thousands_axis(axs[1, 1])
    set_auto_ylim_with_margin(
        axs[1, 1],
        df["summary_total_profit"],
        margin_ratio=0.25,
    )

    style_all_axes(
        axs=axs,
        x_label="Demand variation (%)",
        rotate_x=True,
    )

    fig.suptitle(
        "Impact of demand variation on MTS performance",
        fontsize=13,
        y=1.02,
    )
    fig.tight_layout()

    save_figure(fig, "figure_5_mts_demand_variation")


# ---------------------------------------------------------------------
# Figure 6 — Supply interruption
# ---------------------------------------------------------------------

def plot_supply_interruption(
    csv_path: Path = MTS_CASE_DIR / "results_shortage.csv",
) -> None:
    df = read_results(csv_path)
    df = df.sort_values("shortage_duration_weeks")

    required_columns = [
        "shortage_duration_weeks",
        "service_level_percent",
        "average_raw_material_oh",
        "average_finished_goods",
        "production_plan_fulfillment_percent",
        "summary_total_profit",
    ]
    validate_columns(df, required_columns, "Supply interruption figure")

    x = df["shortage_duration_weeks"].astype(int)

    fig, axs = plt.subplots(2, 2, figsize=(9, 6))

    # (a) Service level
    axs[0, 0].plot(
        x,
        df["service_level_percent"],
        marker="o",
    )
    axs[0, 0].set_title("(a) Service level")
    axs[0, 0].set_ylabel("Service level (%)")
    axs[0, 0].set_ylim(0, 110)

    # (b) Inventory buffers normalized
    plot_inventory_buffers_normalized(
        ax=axs[0, 1],
        x=x,
        df=df,
    )

    # (c) Production fulfilment
    axs[1, 0].plot(
        x,
        df["production_plan_fulfillment_percent"],
        marker="o",
    )
    axs[1, 0].set_title("(c) Production fulfilment")
    axs[1, 0].set_ylabel("Production fulfilment (%)")
    axs[1, 0].set_ylim(0, 110)

    # (d) Profit
    axs[1, 1].plot(
        x,
        df["summary_total_profit"],
        marker="o",
    )
    axs[1, 1].set_title("(d) Profit")
    axs[1, 1].set_ylabel("Profit (€)")
    format_thousands_axis(axs[1, 1])
    set_auto_ylim_with_margin(
        axs[1, 1],
        df["summary_total_profit"],
        margin_ratio=0.25,
    )

    style_all_axes(
        axs=axs,
        x_label="Supply interruption duration (weeks)",
    )

    for ax in axs.flat:
        ax.set_xticks(x)

    fig.suptitle(
        "Impact of supply interruptions on MTS resilience",
        fontsize=13,
        y=1.02,
    )
    fig.tight_layout()

    save_figure(fig, "figure_6_mts_supply_interruption")


# ---------------------------------------------------------------------
# Figure 7 — Lead-time shock
# ---------------------------------------------------------------------

def plot_lead_time_shock(
    csv_path: Path = MTS_CASE_DIR / "results_lead_time_shock.csv",
) -> None:
    df = read_results(csv_path)
    df = df.sort_values("lead_time_weeks")

    required_columns = [
        "lead_time_weeks",
        "service_level_percent",
        "average_raw_material_oh",
        "average_finished_goods",
        "production_plan_fulfillment_percent",
        "summary_total_profit",
    ]
    validate_columns(df, required_columns, "Lead-time shock figure")

    x = df["lead_time_weeks"].astype(int)

    fig, axs = plt.subplots(2, 2, figsize=(9, 6))

    # (a) Service level
    axs[0, 0].plot(
        x,
        df["service_level_percent"],
        marker="o",
    )
    axs[0, 0].set_title("(a) Service level")
    axs[0, 0].set_ylabel("Service level (%)")
    axs[0, 0].set_ylim(0, 110)

    # (b) Inventory buffers normalized
    plot_inventory_buffers_normalized(
        ax=axs[0, 1],
        x=x,
        df=df,
    )

    # (c) Production fulfilment
    axs[1, 0].plot(
        x,
        df["production_plan_fulfillment_percent"],
        marker="o",
    )
    axs[1, 0].set_title("(c) Production fulfilment")
    axs[1, 0].set_ylabel("Production fulfilment (%)")
    axs[1, 0].set_ylim(0, 110)

    # (d) Profit
    axs[1, 1].plot(
        x,
        df["summary_total_profit"],
        marker="o",
    )
    axs[1, 1].set_title("(d) Profit")
    axs[1, 1].set_ylabel("Profit (€)")
    format_thousands_axis(axs[1, 1])
    set_auto_ylim_with_margin(
        axs[1, 1],
        df["summary_total_profit"],
        margin_ratio=0.25,
    )

    style_all_axes(
        axs=axs,
        x_label="Supplier lead time (weeks)",
    )

    for ax in axs.flat:
        ax.set_xticks(x)

    fig.suptitle(
        "Sensitivity of MTS performance to supplier lead-time increases",
        fontsize=13,
        y=1.02,
    )
    fig.tight_layout()

    save_figure(fig, "figure_7_mts_lead_time_shock")


# ---------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------

def generate_all_mts_reporting_figures() -> None:
    plot_demand_variation()
    plot_supply_interruption()
    plot_lead_time_shock()


if __name__ == "__main__":
    generate_all_mts_reporting_figures()