
import pandas as pd

def compute_costs(orders, config):

    rows = []

    for o in orders:

        # -------- LABOUR COST --------
        labour_cost = getattr(o, "labour_cost", 0)

        # -------- MATERIAL COST --------
        material_cost = getattr(o, "purchasing_cost", 0)

        # -------- PRODUCTION COST --------
        production_cost = getattr(o, "production_cost", 0)

        # -------- TRANSPORT COST --------
        transport_cost = getattr(o, "transport_cost", 0)

        # -------- TOTAL --------
        total_cost = (
            labour_cost
            + material_cost
            + production_cost
            + transport_cost
        )

        rows.append({
            "order": o.id,
            "labour_cost": labour_cost,
            "material_cost": material_cost,            
            "transport_cost": transport_cost,
            "total_cost": total_cost
        })

    return pd.DataFrame(rows)
