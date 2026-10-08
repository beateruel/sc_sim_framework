
from datetime import timedelta
import pandas as pd


def compute_otif(orders, base_date):
    rows = []

    for o in orders:
        if o.expected_delivery_date is None:
            continue

        if not hasattr(o, "finish_time") or o.finish_time is None:
            on_time = False
            finish_date = None
        else:
            finish_date = base_date + timedelta(hours=o.finish_time)
            on_time = finish_date <= o.expected_delivery_date

        rows.append(
            {
                "order": o.id,
                "finish_time": getattr(o, "finish_time", None),
                "finish_date": finish_date,
                "expected_delivery_date": o.expected_delivery_date,
                "on_time": on_time,
            }
        )

    df = pd.DataFrame(rows)

    service_level = (
        df["on_time"].mean()
        if len(df) > 0
        else 0.0
    )

    return df, service_level
