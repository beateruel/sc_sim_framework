"""
Publication-oriented reporting figures for the MTO case.

Input CSV files:
    results/experiments/mto_case/results_demand_variation.csv
    results/experiments/mto_case/results_prototyping.csv

Output figures:
    results/experiments/mto_case/visualization/
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
MTO_CASE_DIR = RESULTS_DIR / "experiments" / "mto_case"

OUTPUT_DIR = MTO_CASE_DIR / "visualization"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def read_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

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


def validate_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    figure_name: str,
) -> None:
    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise KeyError(
            f"{figure_name} cannot be generated. Missing columns: {missing}"
        )


def style_all_axes(
    axs,
    x_label: str,
    rotate_x: bool = False,
) -> None:
    for ax in axs.flat:
        ax.set_xlabel(x_label)
        apply_axis_style(ax)

        if rotate_x:
            ax.tick_params(axis="x", rotation=30)


def get_physical_digital_rows(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Return physical and digital rows from the prototyping results.
    """

    if "prototyping_type" not in df.columns:
        raise KeyError("Missing column: prototyping_type")

    physical = df[df["prototyping_type"].str.upper() == "PHYSICAL"]
    digital = df[df["prototyping_type"].str.upper() == "DIGITAL"]

    if physical.empty or digital.empty:
        raise ValueError(
            "The prototyping CSV must include one PHYSICAL row and one DIGITAL row."
        )

    return physical.iloc[0], digital.iloc[0]


def compute_relative_improvements(
    physical: pd.Series,
    digital: pd.Series,
) -> pd.DataFrame:
    """
    Compute percentage changes from physical to digital prototyping.

    Positive values indicate improvement:
    - cost reduction is positive,
    - profit increase is positive,
    - waste reduction is positive,
    - emissions reduction is positive.
    """

    cost_reduction = (
        (physical["total_cost"] - digital["total_cost"])
        / physical["total_cost"]
        * 100
    )

    profit_increase = (
        (digital["total_recognized_profit"] - physical["total_recognized_profit"])
        / physical["total_recognized_profit"]
        * 100
    )

    waste_reduction = (
        (physical["total_waste"] - digital["total_waste"])
        / physical["total_waste"]
        * 100
    )

    emissions_reduction = (
        (physical["total_emissions"] - digital["total_emissions"])
        / physical["total_emissions"]
        * 100
    )

    return pd.DataFrame(
        [
            {
                "indicator": "Cost reduction",
                "improvement_percent": cost_reduction,
            },
            {
                "indicator": "Profit increase",
                "improvement_percent": profit_increase,
            },
            {
                "indicator": "Waste reduction",
                "improvement_percent": waste_reduction,
            },
            {
                "indicator": "Emissions reduction",
                "improvement_percent": emissions_reduction,
            },
        ]
    )


# ---------------------------------------------------------------------
# Figure 8 — Demand variation
# ---------------------------------------------------------------------

def plot_demand_variation(
    csv_path: Path = MTO_CASE_DIR / "results_demand_variation.csv",
) -> None:
    df = read_results(csv_path)
    df = df.sort_values("demand_variation_percent")

    required_columns = [
        "demand_variation_percent",
        "service_level_percent",        
        "total_recognized_profit",
        "lost_revenue_due_to_late_orders",
    ]

    validate_columns(
        df,
        required_columns,
        "Demand variation figure",
    )

    x_labels = demand_labels(
        df["demand_variation_percent"]
    )

    fig, axs = plt.subplots(1, 3, figsize=(13, 4))

       # (a) Service level
    axs[0].plot(
        x_labels,
        df["service_level_percent"],
        marker="o",
    )
    axs[0].set_title("(a) Service level")
    axs[0].set_ylabel("Service level (%)")
    axs[0].set_ylim(0, 110)

    # (b) Recognized profit
    axs[1].plot(
        x_labels,
        df["total_recognized_profit"],
        marker="o",
    )
    axs[1].set_title("(b) Recognized profit")
    axs[1].set_ylabel("Recognized profit (€)")
    format_thousands_axis(axs[1])

    # (c) Lost revenue
    axs[2].plot(
        x_labels,
        df["lost_revenue_due_to_late_orders"],
        marker="o",
    )
    axs[2].set_title("(c) Lost revenue due to late orders")
    axs[2].set_ylabel("Lost revenue (€)")
    format_thousands_axis(axs[2])

    style_all_axes(
        axs=axs,
        x_label="Demand variation (%)",
        rotate_x=True,
    )

    fig.suptitle(
        "Impact of demand variation on MTO performance",
        fontsize=13,
        y=1.02,
    )

    fig.tight_layout()

    save_figure(
        fig,
        "figure_8_mto_demand_variation",
    )


# ---------------------------------------------------------------------
# Figure 9 — Digital prototyping
# ---------------------------------------------------------------------

def plot_digital_prototyping(
    csv_path: Path = MTO_CASE_DIR / "results_prototyping.csv",
) -> None:
    df = read_results(csv_path)

    required_columns = [
        "prototyping_type",
        "total_cost",
        "total_recognized_profit",
        "total_emissions",
        "total_waste",
    ]

    validate_columns(
        df,
        required_columns,
        "Digital prototyping figure",
    )

    physical, digital = get_physical_digital_rows(df)
    improvements = compute_relative_improvements(physical, digital)

    labels = df["prototyping_type"].str.upper()

    fig, axs = plt.subplots(2, 2, figsize=(9, 6))

    # (a) Total cost
    axs[0, 0].bar(
        labels,
        df["total_cost"],
    )
    axs[0, 0].set_title("(a) Total cost")
    axs[0, 0].set_ylabel("Total Cost (€)")
    format_thousands_axis(axs[0, 0])

    # (b) Recognized profit
    axs[0, 1].bar(
        labels,
        df["total_recognized_profit"],
    )
    axs[0, 1].set_title("(b) Recognized profit")
    axs[0, 1].set_ylabel("Recognized Profit (€)")
    format_thousands_axis(axs[0, 1])

    # (c) Total waste
    axs[1, 0].bar(
        labels,
        df["total_waste"],
    )
    axs[1, 0].set_title("(c) Total waste")
    axs[1, 0].set_ylabel("Waste (kg)")

   # (d) Recognized profit margin

    axs[1, 1].bar(
        df["prototyping_type"],
        df["recognized_profit_margin"] * 100,
    )

    axs[1, 1].set_title("(d) Recognized profit margin")
    axs[1, 1].set_ylabel("Recognized profit margin (%)")
    # The relative-improvement panel has indicators on the x-axis,
    # not scenarios.
    axs[1, 1].set_xlabel("")
    axs[1, 1].set_ylim(
        0,
        max(df["recognized_profit_margin"] * 100) * 1.2
    )
    for i, value in enumerate(df["recognized_profit_margin"] * 100):
        axs[1, 1].text(
            i,
            value + 0.5,
            f"{value:.1f}%",
            ha="center",
        )



    fig.suptitle(
        "Impact of digital prototyping on MTO sustainability performance",
        fontsize=13,
        y=1.02,
    )

    fig.tight_layout()

    save_figure(
        fig,
        "figure_9_mto_digital_prototyping",
    )


# ---------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------

def generate_all_mto_reporting_figures() -> None:
    plot_demand_variation()
    plot_digital_prototyping()


if __name__ == "__main__":
    generate_all_mto_reporting_figures()