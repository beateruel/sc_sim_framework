
from datetime import datetime
import json
from core.mto.entities.order import Order


def load_orders_from_json(path):

    with open(path, "r") as f:
        data = json.load(f)

    orders = []

    for o in data["orders"]:

        # dates
        init_date = datetime.strptime(o["init_date"], "%d/%m/%Y")
        expected_delivery_date = datetime.strptime(o["expected_delivery_date"], "%d/%m/%Y")
        init_fullfilment_date = datetime.strptime(o["init_fullfilment_date"], "%d/%m/%Y")

        # create order
        order = Order(
            order_id=o["id"],
            init_date=init_date,
            expected_delivery_date=expected_delivery_date,
            init_fullfilment_date=init_fullfilment_date
        )

        # -----------------------------------
        # quantity and product 
        # -----------------------------------
        order.sample_units = o.get("sample_units", 5)
        order.production_units = o["number_of_units"]

        order.material_per_piece = o["product_material_per_piece"]
        order.number_styles = o.get("number_styles", 1)

        # -----------------------------------
        # prices
        # -----------------------------------
        order.selling_price = o.get("selling_price", 0)
        
        order.supplier_material = o.get("supplier_material", {})
        order.supplier_sample = o.get("supplier_sample", {})

        order.supplier_material_price = order.supplier_material.get("price", 0)
        order.supplier_sample_price = order.supplier_sample.get("price", 0)


        # -----------------------------------
        # client
        # -----------------------------------
        order.client = o.get("client", {})

        
        order.proto_transport = order.client.get(
            "prototype_distribution_mode_of_transport", "ROAD"
        )

        order.full_transport = order.client.get(
            "fullfilment_distribution_mode_of_transport", "ROAD"
        )
        
        # -----------------------------
        # INITIAL COSTS
        # -----------------------------
        order.purchasing_cost = 0
        order.production_cost = 0
        order.transport_cost = 0


       
        # -----------------------------------
        #  BACKUP RAW DATA (optional)
        # -----------------------------------
        order.data = o 



        orders.append(order)

    return orders


def load_config(path):
    with open(path, "r") as f:
        return json.load(f)

