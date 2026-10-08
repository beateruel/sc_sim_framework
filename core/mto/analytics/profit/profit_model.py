import pandas as pd


def compute_profit(orders, base_date):
    rows = []

    for o in orders:
        committed_revenue = o.production_units * o.selling_price

        total_cost = (
            o.labour_cost
            + o.purchasing_cost
            + o.transport_cost
            + o.production_cost
        )

        on_time = _is_on_time(o, base_date)

        recognized_revenue = committed_revenue if on_time else 0.0

        committed_profit = committed_revenue - total_cost
        recognized_profit = recognized_revenue - total_cost

        rows.append(
            {
                "order": o.id,
                "production_units": o.production_units,
                "selling_price": o.selling_price,
                "on_time": on_time,
                "committed_revenue": committed_revenue,
                "recognized_revenue": recognized_revenue,
                "total_cost": total_cost,
                "committed_profit": committed_profit,
                "recognized_profit": recognized_profit,
            }
        )

    return pd.DataFrame(rows)


def _is_on_time(order, base_date) -> bool:
    if order.expected_delivery_date is None:
        return False

    if not hasattr(order, "finish_time") or order.finish_time is None:
        return False

    expected_delay = (
        order.expected_delivery_date - base_date
    ).days * 24

    return order.finish_time <= expected_delay