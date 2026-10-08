
from core.mto.workflows import approval, prototype,fulfilment


def run_order_flow(env, order, resources, config):

    yield from approval.run(env, order, resources, config)

    yield from prototype.run(env, order, resources, config, phase="proto")

    yield from fulfilment.run(env, order, resources, config, phase="full")

    order.finish_time = env.now
