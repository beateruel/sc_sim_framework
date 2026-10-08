
def run(env, order, resources, config, phase):

    phase_name = f"{phase}_delivery"

    t_now = env.now
    t_prev = order.last_end_time if order.last_end_time is not None else t_now

    start_wait = max(t_now, t_prev)

    if start_wait > t_now:
        yield env.timeout(start_wait - t_now)

    order.request_times[phase_name] = start_wait

   
    with resources.logistics.request(priority=3) as req:
        yield req

        #transport mode, depending on the phase
        if phase == "proto":
            mode = order.data["client"]["prototype_distribution_mode_of_transport"]
            if mode == "AIR":
                transport_duration = config["times"]["product_air_delivery_time_h"]
                order.transport_cost+=config["economic"]["sample_distribution_air_transport_cost_eur"]
                
            else:
                transport_duration = config["times"]["product_road_delivery_time_h"]
                order.transport_cost+=config["economic"]["sample_distribution_road_transport_cost_eur"]
               
        else:
            mode = order.data["client"]["fullfilment_distribution_mode_of_transport"]
            if mode == "AIR":
                transport_duration = config["times"]["product_air_delivery_time_h"]
                order.transport_cost+=config["economic"]["product_distribution_air_transport_cost_eur"]                
            else:
                transport_duration = config["times"]["product_road_delivery_time_h"]
                order.transport_cost+=config["economic"]["product_distribution_road_transport_cost_eur"]               
                       

        # -----------------------------
        # storage, exclusively for fulfillment
        # -----------------------------
        if phase == "full" and order.expected_delivery_date is not None:

            base_date = config["base_date"]
            expected_time = (order.expected_delivery_date - base_date).days * 24

            release_time = expected_time - transport_duration

            if env.now < release_time:
                wait = release_time - env.now
                print(f"{order.id} storing {wait} before delivery departure")
                yield env.timeout(wait)

        # -----------------------------
        # start delivery
        # -----------------------------
        order.start_times[phase_name] = env.now

        yield env.timeout(transport_duration)

        # -----------------------------
        # FIN
        # -----------------------------
        order.end_times[phase_name] = env.now
        order.last_end_time = env.now

        order.state["delivered"] = True
        

        print(f"{order.id} delivered at {env.now}")
