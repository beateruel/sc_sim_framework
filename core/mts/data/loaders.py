import json
import pandas as pd


def load_config(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_weekly_demand_mts(file_path, variation=0):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    rows = []
    global_week = 0

    for month_data in data["demand"]:
        month = month_data["month"]

        for _ in range(4):
            for item in month_data["items"]:
                rows.append({
                    "month": month,
                    "week": global_week,
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity_units": int(
                        item["quantity_units"] * (1 + variation) / 4
                    ),
                })

            global_week += 1

    return pd.DataFrame(rows)


def load_products_bom(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    rows = []

    for product_data in data.get("bill_of_materials", []):
        for material in product_data.get("materials", []):
            rows.append({
                "product_id": product_data["product_id"],
                "product_name": product_data["product_name"],
                "total_weight_g": product_data["total_weight_g"],
                "cycle_time_s": product_data["cycle_time_s"],
                "production_rate_units_per_cycle": product_data[
                    "production_rate_units_per_cycle"
                ],
                "setup_time_min": product_data["setup_time_min"],
                "quality_check_time_min": product_data[
                    "quality_check_time_min"
                ],
                "batch_size_units": product_data["batch_size_units"],
                "safety_stock_units": product_data["safety_stock_units"],
                "material_id": material["material_id"],
                "material_display_name": material["material_display_name"],
                "material_name": material["material_name"],
                "material_quantity_g_per_unit": material[
                    "material_quantity_g_per_unit"
                ],
            })

    return pd.DataFrame(rows)


def load_suppliers(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    rows = []

    for supplier_data in data.get("suppliers", []):
        rows.append({
            "supplier_id": supplier_data["supplier_id"],
            "material_id": supplier_data["material_id"],
            "material_display_name": supplier_data["material_display_name"],
            "supplier_name": supplier_data["supplier_name"],
            "supplier_location": supplier_data["supplier_location"],
            "distance_km": supplier_data["distance_km"],
            "min_price_eur_per_kg": supplier_data["min_price_eur_per_kg"],
            "max_price_eur_per_kg": supplier_data["max_price_eur_per_kg"],
            "reorder_quantity_kg": supplier_data["reorder_quantity_kg"],
            "reorder_point_weeks": supplier_data["reorder_point_weeks"],
            "lead_time_weeks": supplier_data["lead_time_weeks"],
            "delivery_quantity_kg": supplier_data["delivery_quantity_kg"],
            "delivery_time_weeks": supplier_data["delivery_time_weeks"],
            "safety_stock_kg": supplier_data["safety_stock_kg"],
            "delivery_mode": supplier_data["delivery_mode"],
        })

    return pd.DataFrame(rows)