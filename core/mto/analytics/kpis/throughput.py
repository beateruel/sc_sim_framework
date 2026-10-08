import pandas as pd

def compute_throughput(orders):

    finished = [

        o.finish_time for o in orders
        if hasattr(o, "finish_time") and o.finish_time is not None

    ]

    if not finished:
        return None

    max_time = max(finished)

    throughput = len(finished) / max_time

    return throughput