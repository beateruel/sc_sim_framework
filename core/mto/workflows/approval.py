from core.mto.utils.time_utils import working_time

def run(env, order, resources, config):

    phase = "approval"

    
    start_wait = env.now
    if order.last_end_time is not None:
        start_wait = max(start_wait, order.last_end_time)

    if start_wait > env.now:
        yield env.timeout(start_wait - env.now)

    order.request_times[phase] = start_wait

    print(f"{order.id} requests approval at {start_wait}")

    
    with resources.office.request() as req:
        yield req

        order.start_times[phase] = env.now

        duration = config["times"]["approval_phase_min_time_h"]

        yield from working_time(env, duration)

        order.end_times[phase] = env.now
        order.last_end_time = env.now
        
        order.office_time += duration
        order.labour_cost += duration * config["economic"]["office_work_salary_eur_per_h"] 

        
        office_energy = order.office_time * config["environmental"]["office_energy_consumption_kwh_per_h"]
        order.production_emissions += office_energy * config["environmental"]["grid_carbon_intensity_gco2_per_kwh"]



        order.state["approval_done"] = True
