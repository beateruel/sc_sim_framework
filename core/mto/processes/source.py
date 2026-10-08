from core.mto.utils.time_utils import working_time


def run(env, order, resources, config, phase):

    phase_name = f"{phase}_sourcing"

    # -----------------------------
    # START CONTROL
    # -----------------------------
    if "proto" in phase:

        start_wait = env.now
        if order.last_end_time is not None:
            start_wait = max(start_wait, order.last_end_time)

        if start_wait > env.now:
            yield env.timeout(start_wait - env.now)

        order.request_times[phase_name] = start_wait

        # Prototype uses logistics resource
        with resources.logistics.request(priority=3) as req:
            yield req
            order.start_times[phase_name] = env.now

    elif "full" in phase:

        start_wait = order.fulfilment_release_time

        if start_wait > env.now:
            yield env.timeout(start_wait - env.now)

        order.request_times[phase_name] = start_wait
        order.start_times[phase_name] = env.now

    # =============================
    # PROTOTYPE → ROP SYSTEM
    # =============================
    if "proto" in phase:

        inventory = resources.sample_inventory
        log = resources.sample_log

        reorder_point = config["operational"]["sample_reorder_point_units"]
        reorder_qty = config["operational"]["sample_reorder_quantity_units"]

        supplier_price = order.supplier_sample_price

        # reorder if below threshold
        if inventory.level < reorder_point:

            print(f"{order.id} REORDER SAMPLE | level={inventory.level}")

            yield inventory.put(reorder_qty)

            order.purchasing_cost += reorder_qty * config["economic"]["sample_material_unit_price_eur"]

            log.append((env.now, inventory.level))

    # =============================
    # FULFILMENT → GUARANTEED MATERIAL
    # =============================
    else:

        inventory = resources.production_inventory
        log = resources.production_log

        amount = order.production_units * order.material_per_piece
        supplier_price = order.supplier_material_price

        #ALWAYS ensure enough material for the order
        print(f"{order.id} ORDER FULL MATERIAL | amount={amount}")

        yield inventory.put(amount)

        order.purchasing_cost += amount * config["economic"]["product_material_unit_price_eur"]

        log.append((env.now, inventory.level))

    # -----------------------------
    # TRANSPORT TIME
    # -----------------------------
    if "proto" in phase:

        duration = config["times"]["sample_reception_road_transport_time_h"]

    else:
        mode = order.supplier_material.get(
            "material_reception_mode_of_transport",
            "ROAD"
        )

        if mode == "AIR":
            duration = config["times"]["fulfillment_material_air_transport_time_h"]
        else:
            duration = config["times"]["fulfillment_material_road_transport_time_h"]

    yield from working_time(env, duration)

    # -----------------------------
    # END
    # -----------------------------
    order.end_times[phase_name] = env.now
    order.last_end_time = env.now
