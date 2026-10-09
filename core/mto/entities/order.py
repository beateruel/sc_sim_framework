
from datetime import datetime

class Order:
    def __init__(self, order_id, init_date=None, expected_delivery_date=None, init_fullfilment_date=None):

        self.id = order_id
        self.state = {}
        self.prototyping_type = None

        # dates
        self.init_date = init_date
        self.expected_delivery_date = expected_delivery_date
        self.init_fullfilment_date = init_fullfilment_date

        # tracking simulation
        self.waiting_time = 0
        
        self.processing_time = 0   #  TOTAL WORK TIME

        self.office_time = 0       # office work (approval_desing)
        self.production_time = 0   # shopfloor work


        self.start_times = {}
        self.end_times = {}
        self.request_times = {}
        self.last_end_time = None
        self.arrival_time = None
        self.finish_time = None

        # prototyping and fulfillment make
        self.sample_units = None
        self.production_units = None
        self.material_per_piece = None

        # transport
        self.proto_transport = None
        self.full_transport = None

        # partners
        self.client = None
        self.supplier_material = None
        self.supplier_sample = None

        # costs / sustainability
        self.waste = 0
        self.labour_cost =0
        self.transport_cost = 0
        self.purchasing_cost=0
        self.production_emissions =0
        self.transport_emisions =0

        #business
        self.selling_price=0
        self.revenue=0
        self.profit=0
        self.sample_distance= 0

        # raw backup (opcional)
        self.data = None
