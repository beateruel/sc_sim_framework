
from core.mto.processes import source, make, deliver
from core.mto.utils.time_utils import working_time

def run(env, order, resources, config, phase="proto"):

    # -------------------
    # DESIGN 
    # -------------------
    start_wait = env.now

    with resources.designer.request() as req:
        yield req

        waiting = env.now - start_wait
        order.waiting_time += waiting

        print(f"{order.id} waited {waiting} before design")
        print(f"{order.id} starts prototype design at {env.now}")

        order.start_times["prototype_design"] = env.now

        duration = config["times"]["prototyping_design_min_time_h"]

        # digital --> more time
        if order.prototyping_type == "DIGITAL":
            duration *= 1.5

        yield from working_time(env, duration)

        order.end_times["prototype_design"] = env.now
        order.last_end_time = env.now
        order.labour_cost += duration * config["economic"]["office_work_salary_eur_per_h"]
        office_energy = order.office_time * config["environmental"]["office_energy_consumption_kwh_per_h"]
        order.production_emissions += office_energy * config["environmental"]["grid_carbon_intensity_gco2_per_kwh"]

    # -------------------
    # DIGITAL 
    # -------------------
    if order.prototyping_type == "DIGITAL":

        print(f"{order.id} DIGITAL PROTOTYPE → skipping sourcing/make/delivery")

        order.state["prototype_done"] = True
        return

    # -------------------
    # PHYSICAL 
    # -------------------
    yield from source.run(env, order, resources, config, phase="proto")
    yield from make.run(env, order, resources, config, phase="proto")
    yield from deliver.run(env, order, resources, config, phase="proto")

    order.state["prototype_done"] = True
