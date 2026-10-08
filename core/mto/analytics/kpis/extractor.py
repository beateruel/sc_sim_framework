import pandas as pd

def orders_to_dataframe(orders):

    rows = []

    for o in orders:
        for phase in o.start_times:

            rows.append({
                "order": o.id,
                "phase": phase,
                "start": o.start_times[phase],
                "end": o.end_times.get(phase),
                "finish_time": getattr(o, "finish_time", None),
                "expected_delivery_date": o.expected_delivery_date
            })

    return pd.DataFrame(rows)