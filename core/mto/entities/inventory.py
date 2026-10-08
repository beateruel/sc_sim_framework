def inventory_monitor(env, resources, config):
    """
    Continuous inventory monitoring.
    Checks stock periodically and triggers reorder if needed.
    """

    reorder_point = config["operational"]["sample_reorder_point_units"]
    reorder_qty = config["operational"]["sample_reorder_quantity_units"]

    while True:

        inventory = resources.sample_inventory

        # check condition
        if inventory.level < reorder_point:

            print(f"MONITOR REORDER | level={inventory.level}")

            yield inventory.put(reorder_qty)

            # log inventory
            resources.sample_log.append((env.now, inventory.level))

        # check every few hours
        yield env.timeout(4)   # puedes ajustar (ej: 1h, 8h, 24h)