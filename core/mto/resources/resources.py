
import simpy

class Resources:

    def __init__(self, env, config):

        
        # -----------------------------
        # HUMAN RESOURCES
        # -----------------------------

        self.office = simpy.Resource(env, capacity=6)
        self.designer = simpy.Resource(env, capacity=6)
        self.operator = simpy.PriorityResource(env, capacity=6)
        self.logistics = simpy.PriorityResource(env, capacity=6)

        
        # -----------------------------
        # INVENTORIES
        # -----------------------------


        # Prototype materials (samples)
        self.sample_inventory = simpy.Container(
            env,
            capacity=500,
            init=100   # avoid initial stockout
        )

        # Production materials
        self.production_inventory = simpy.Container(
            env,
            capacity=5000,
            init=500   
        )

        
        # -----------------------------
        # INVENTORY LOGS (for plotting)
        # -----------------------------
        self.sample_log = []
        self.production_log = []


        # Finished goods inventory (para MTS distribution)
        self.finished_goods_inventory = simpy.Container(
            env,
            capacity=10000,
            init=0
        )

        # Inventory logs para MTS
        self.finished_goods_log = []

        # Track inventory levels per product (para MTS multi-producto)
        self.product_inventory = {}  # {product_id: level}
        self.product_inventory_log = {}  # {product_id: [(time, level), ...]}

        # Store config reference (necesario para MTS)
        self.config = config
        self.env = env


