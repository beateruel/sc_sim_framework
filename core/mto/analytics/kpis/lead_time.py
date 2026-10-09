import pandas as pd

def compute_lead_time(orders):

    data = []

    for o in orders:

        if o.finish_time is not None and o.arrival_time is not None:
            lead_time = o.finish_time - o.arrival_time
        else:
            lead_time = None

        data.append({
            "order": o.id,
            "lead_time_hours": lead_time
        })

    return pd.DataFrame(data)