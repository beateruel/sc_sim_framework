import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta


def sim_to_date(sim_time, base_date):
    """Convert simulation time (hours) into datetime."""
    return base_date + timedelta(hours=sim_time)


def plot_inventory(log, base_date, title="Inventory", reorder_point=None, save_path=None):
    """
    Plot inventory level over time.

    Parameters:
    - log: list of tuples (time, level)
    - base_date: datetime
    - title: str
    - reorder_point: optional (draw horizontal line)
    - save_path: optional (save figure)
    """

    if not log:
        print(f"No data for {title}")
        return

    # -----------------------------
    # DATA PREPARATION
    # -----------------------------
     
    # sort log by time (important)
    log = sorted(log, key=lambda x: x[0])
   
    times = [t for t, _ in log]
    levels = [lvl for _, lvl in log]  


    dates = [sim_to_date(t, base_date) for t in times]

    # -----------------------------
    # PLOT
    # -----------------------------
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.step(dates, levels, where='post', linewidth=2)

    # -----------------------------
    # OPTIONAL: REORDER LINE
    # -----------------------------
    if reorder_point is not None:
        ax.axhline(
            y=reorder_point,
            color='red',
            linestyle='--',
            linewidth=2,
            label='Reorder point'
        )
        ax.legend()

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
    ax.set_xlim(left=sim_to_date(0, base_date))
    #ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.tight_layout()

    # -----------------------------
    # SAVE / SHOW
    # -----------------------------
    if save_path:
        plt.savefig(save_path, dpi=300)

    #plt.show()