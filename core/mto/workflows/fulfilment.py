# from core.mto.processes import source, make, deliver

# def run(env, order, resources, config, phase="full"):

#     base_date = config["base_date"]
    
   
#     proto_end = order.end_times["proto_delivery"]

#     t_init = (order.init_fullfilment_date - base_date).total_seconds() / 3600
      
#     if env.now < proto_end:
#         yield env.timeout(proto_end - env.now)

#     start_time = max(env.now, t_init)

#     if env.now < start_time:
#         yield env.timeout(start_time - env.now)
  

   
#     order.last_end_time = env.now
#     order.fulfilment_release_time = env.now    
   
#     order.request_times["full_sourcing"] = env.now

#     yield from source.run(env, order, resources, config, phase="full")
#     yield from make.run(env, order, resources, config, phase="full")
#     yield from deliver.run(env, order, resources, config, phase="full")

#     order.state["fulfilment_done"] = True
from core.mto.processes import source, make, deliver


def run(env, order, resources, config, phase="full"):

    base_date = config["base_date"]

    t_init = (
        order.init_fullfilment_date - base_date
    ).total_seconds() / 3600

    if order.prototyping_type == "PHYSICAL":
        proto_end = order.end_times["proto_delivery"]
    else:
        proto_end = (
            max(order.end_times.values())
            if order.end_times
            else env.now
        )

    start_time = max(
        proto_end,
        t_init,
        env.now,
    )

    if env.now < start_time:
        yield env.timeout(
            start_time - env.now
        )

    order.last_end_time = env.now
    order.fulfilment_release_time = env.now

    order.request_times["full_sourcing"] = env.now

    yield from source.run(
        env,
        order,
        resources,
        config,
        phase="full",
    )

    yield from make.run(
        env,
        order,
        resources,
        config,
        phase="full",
    )

    yield from deliver.run(
        env,
        order,
        resources,
        config,
        phase="full",
    )

    order.state["fulfilment_done"] = True