import matplotlib.pyplot as plt
from datetime import timedelta
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches
from datetime import timedelta


def sim_to_date(sim_time, base_date):
    """Convert simulation time (hours) into datetime."""
    return base_date + timedelta(hours=sim_time)


def plot_gantt_clean(orders, base_date, save_path="gantt_clean.png"):
    """Clean Gantt chart without calendar overlay (recommended for clarity)."""

    fig, ax = plt.subplots(figsize=(16, 9))

    # Color map
    colors = {
        "approval": "#e8d5b7",

        "prototype_design": "#d9d9d9",
        "proto_sourcing": "#bdbdbd",
        "proto_make": "#969696",
        "proto_delivery": "#737373",

        "full_sourcing": "#7dd3c7",
        "full_make": "#41bfb3",
        "full_delivery": "#137f7f"
    }

    labels_map = {
        "approval": "Approval",
        "prototype_design": "Prototype - Design",
        "proto_sourcing": "Prototype - Sourcing",
        "proto_make": "Prototype - Make",
        "proto_delivery": "Prototype - Delivery",
        "full_sourcing": "Fulfilment - Sourcing",
        "full_make": "Fulfilment - Make",
        "full_delivery": "Fulfilment - Delivery"
    }

    y_pos = 0
    y_labels = []

    for o in orders:
        phases = sorted(o.start_times.keys(), key=lambda p: o.start_times[p])

        for phase in phases:
            if phase not in o.end_times:
                continue

            start_sim = o.start_times[phase]
            end_sim = o.end_times[phase]
            request_sim = o.request_times.get(phase, start_sim)

            start_date = sim_to_date(start_sim, base_date)
            end_date = sim_to_date(end_sim, base_date)
            request_date = sim_to_date(request_sim, base_date)

            # Waiting time
            if request_sim < start_sim:
                ax.hlines(
                    y=y_pos,
                    xmin=mdates.date2num(request_date),
                    xmax=mdates.date2num(start_date),
                    colors="gray",
                    linestyles="dashed",
                    linewidth=2
                )

            # Process bar
            ax.barh(
                y_pos,
                mdates.date2num(end_date) - mdates.date2num(start_date),
                left=mdates.date2num(start_date),
                color=colors.get(phase, "gray"),
                edgecolor="black",
                height=0.7
            )

        # Expected delivery
        if o.expected_delivery_date:
            ax.vlines(
                mdates.date2num(o.expected_delivery_date),
                y_pos - 0.4,
                y_pos + 0.4,
                colors="red",
                linewidth=2
            )

        # Fulfilment start
        if o.init_fullfilment_date:
            ax.vlines(
                mdates.date2num(o.init_fullfilment_date),
                y_pos - 0.4,
                y_pos + 0.4,
                colors="black",
                linestyles="dashed"
            )

        y_labels.append(o.id)
        y_pos += 1

    # Axes
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))

    plt.xticks(rotation=45)
    ax.grid(True, axis='x', linestyle='--', alpha=0.4)

    ax.axvline(mdates.date2num(base_date), color="black", linewidth=2)

    # Legend
    legend_elements = [
        Line2D([0], [0], color='gray', linestyle='--', label='Waiting time'),
        Line2D([0], [0], color='red', lw=2, label='Expected delivery'),
        Line2D([0], [0], color='black', linestyle='--', label='Start fulfilment'),
    ]

    for phase in colors:
        legend_elements.append(
            Line2D([0], [0], color=colors[phase], lw=6, label=labels_map.get(phase, phase))
        )

    ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')

    ax.set_title("Clean Supply Chain Gantt")
    ax.set_xlabel("Date")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    #plt.show()

def plot_inventory(log, base_date, title="Inventory", save_path=None):
    """
    Plot inventory level over time using step plot.

    Parameters:
    - log: list of tuples (time, level)
    - base_date: datetime
    - title: plot title
    - save_path: optional path to save figure
    """

    if not log:
        print("No inventory data to plot.")
        return

    # -----------------------------
    # EXTRACT DATA
    # -----------------------------
    times = [t for t, _ in log]
    levels = [lvl for _, lvl in log]

    # Convert simulation time → real dates
    dates = [base_date + timedelta(hours=t) for t in times]

    # -----------------------------
    # PLOT
    # -----------------------------
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.step(dates, levels, where='post', linewidth=2)

    # -----------------------------
    # AXES
    # -----------------------------
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))

    plt.xticks(rotation=45)

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Inventory level")

    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)

    #plt.show()