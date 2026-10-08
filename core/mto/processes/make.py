from core.mto.utils.time_utils import working_time


def run(env, order, resources, config, phase):

    phase_name = f"{phase}_make"

    # -----------------------------
    # START CONTROL (WAIT FOR PHASE ORDER)
    # -----------------------------
    start_wait = env.now
    if order.last_end_time is not None:
        start_wait = max(start_wait, order.last_end_time)

    if start_wait > env.now:
        yield env.timeout(start_wait - env.now)

    order.request_times[phase_name] = start_wait

    # -----------------------------
    # RESOURCE (operators)
    # -----------------------------
    with resources.operator.request(priority=3) as req:
        yield req

        # -----------------------------
        # SELECT INVENTORY + QUANTITY
        # -----------------------------
        if "proto" in phase:
            quantity = order.sample_units
            inventory = resources.sample_inventory
            log = resources.sample_log


        else:
            quantity = order.production_units
            inventory = resources.production_inventory
            log = resources.production_log

        # -----------------------------
        # VALIDATION
        # -----------------------------
        if quantity is None:
            raise ValueError(f"{order.id} has no quantity defined for phase {phase}")

        amount = quantity * order.material_per_piece

        # -----------------------------
        # WAIT FOR MATERIAL (if needed)
        # -----------------------------
        if inventory.level < amount:
            print(f"{order.id} WAITING MATERIAL | need={amount} available={inventory.level}")

        # blocking until enough material
        yield inventory.get(amount)

        # NOW production truly starts
        order.start_times[phase_name] = env.now

        # log after consumption
        log.append((env.now, inventory.level))

        print(f"{order.id} START MAKE {phase} | quantity={quantity} | remaining={inventory.level}")

        # -----------------------------
        # PRODUCTION TIME
        # -----------------------------
        rate = config["operational"]["product_production_rate_min_units_per_h"]
        duration = quantity / rate

        yield from working_time(env, duration)

        ######
        order.production_time += duration
        order.labour_cost += duration * config["economic"]["operator_work_salary_eur_per_h"] 


        # -----------------------------
        # END
        # -----------------------------
        order.end_times[phase_name] = env.now
        order.last_end_time = env.now

        # -----------------------------
        # WASTE and CO2
        # -----------------------------
        if "proto" in phase:
           order.waste += amount
        else:
            waste_rate = config["environmental"]["product_material_waste_percentage"]
            order.waste += amount * waste_rate
        
        energy = duration * config["environmental"]["shopfloor_energy_consumption_kwh_per_h"]

        order.production_emissions += (
            energy
            * config["environmental"]["grid_carbon_intensity_gco2_per_kwh"]
        )
