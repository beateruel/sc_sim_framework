
class Scheduler:

    def __init__(self, env):
        self.env = env

    def schedule_orders_with_arrivals(self, orders, process_fn):
        """
        orders = lista de tuplas (arrival_time, order)
        """

        for arrival_time, order in orders:
            self.env.process(
                self._launch_after_delay(arrival_time, order, process_fn)
            )

    def _launch_after_delay(self, delay, order, process_fn):
        yield self.env.timeout(delay)
        order.arrival_time = self.env.now
        print(f"Launching {order.id} at time {self.env.now}")
        yield self.env.process(process_fn(order))

