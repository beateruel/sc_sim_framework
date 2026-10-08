from __future__ import annotations

import math
import pandas as pd

from core.mts.entities.inventory import InventoryManager


class MTSMakeProcess:
    def __init__(
        self,
        inventory: InventoryManager,
        weekly_demand: pd.DataFrame,
        products_bom: pd.DataFrame,
        labour_cost_per_hour: float = 17.0,
    ) -> None:
        self.inventory = inventory
        self.weekly_demand = weekly_demand
        self.products_bom = products_bom
        self.labour_cost_per_hour = labour_cost_per_hour

        self.production_log: list[dict] = []
        self.total_production_cost = 0.0

    def execute_week(self, week: int) -> None:
        weekly_demand = self._get_demand_for_week(week)

        if weekly_demand.empty:
            return

        for _, demand_row in weekly_demand.iterrows():
            self._produce_product(
                week=week,
                product_id=str(demand_row["product_id"]),
                product_name=str(demand_row["product_name"]),
                demand_quantity=float(demand_row["quantity_units"]),
            )

    def _produce_product(
        self,
        week: int,
        product_id: str,
        product_name: str,
        demand_quantity: float,
    ) -> None:
        product_bom_rows = self.products_bom[
            self.products_bom["product_id"].astype(str) == product_id
        ]

        if product_bom_rows.empty:
            return

        product_bom = product_bom_rows.iloc[0]

        batch_size = float(product_bom["batch_size_units"])
        safety_stock = float(product_bom["safety_stock_units"])
        current_fg = self.inventory.get_finished_good(product_id)

        projected_fg_after_demand = current_fg - demand_quantity

        if projected_fg_after_demand < safety_stock:
            required_to_target = safety_stock - projected_fg_after_demand
            number_of_batches = math.ceil(required_to_target / batch_size)
        else:
            number_of_batches = 0

        if number_of_batches <= 0:
            self._log_production(
                week=week,
                product_id=product_id,
                product_name=product_name,
                demand_quantity=demand_quantity,
                planned_quantity=0.0,
                produced_quantity=0.0,
                production_time_hours=0.0,
                setup_time_minutes=0.0,
                status="no_production_required",
            )
            return

        planned_quantity = number_of_batches * batch_size

        enough_material = self._consume_materials_for_quantity(
            product_id=product_id,
            quantity=planned_quantity,
            week=week,
        )

        production_time_hours = self._calculate_production_time_hours(
            product_bom=product_bom,
            quantity=planned_quantity,
            number_of_batches=number_of_batches,
        )

        setup_time_minutes = (
            float(product_bom["setup_time_min"]) * number_of_batches
        )

        if enough_material:
            self.inventory.add_finished_good(product_id, planned_quantity)
            self.total_production_cost += (
                production_time_hours * self.labour_cost_per_hour
            )
            produced_quantity = planned_quantity
            status = "produced"
        else:
            produced_quantity = 0.0
            status = "raw_material_stockout"

        self._log_production(
            week=week,
            product_id=product_id,
            product_name=product_name,
            demand_quantity=demand_quantity,
            planned_quantity=planned_quantity,
            produced_quantity=produced_quantity,
            production_time_hours=production_time_hours,
            setup_time_minutes=setup_time_minutes,
            status=status,
        )

    def _consume_materials_for_quantity(
        self,
        product_id: str,
        quantity: float,
        week: int,
    ) -> bool:
        product_materials = self.products_bom[
            self.products_bom["product_id"].astype(str) == str(product_id)
        ]

        requirements = []

        for _, material in product_materials.iterrows():
            material_id = str(material["material_id"])
            material_weight_g = float(material["material_quantity_g_per_unit"])
            required_kg = quantity * material_weight_g / 1000.0
            requirements.append((material_id, required_kg))

        for material_id, required_kg in requirements:
            available_kg = self.inventory.get_raw_material_oh(material_id)

            if available_kg < required_kg:
                self.inventory.stockouts[week] = 1
                self.inventory._register_raw_material_shortage(
                    week=week,
                    material_id=material_id,
                    shortage=required_kg - available_kg,
                )
                return False

        for material_id, required_kg in requirements:
            self.inventory.consume_raw_material(
                material_id=material_id,
                quantity=required_kg,
                week=week,
                allow_partial=False,
            )

        return True

    def _calculate_production_time_hours(
        self,
        product_bom: pd.Series,
        quantity: float,
        number_of_batches: int,
    ) -> float:
        production_rate = float(product_bom["production_rate_units_per_cycle"])
        cycle_time_seconds = float(product_bom["cycle_time_s"])
        setup_time_minutes = float(product_bom["setup_time_min"])
        quality_check_time_minutes = float(product_bom["quality_check_time_min"])

        number_of_cycles = quantity / production_rate
        processing_time_hours = cycle_time_seconds * number_of_cycles / 3600.0

        setup_and_quality_hours = (
            setup_time_minutes * number_of_batches
            + quality_check_time_minutes
        ) / 60.0

        return processing_time_hours + setup_and_quality_hours

    def _get_demand_for_week(self, week: int) -> pd.DataFrame:
        return self.weekly_demand[
            self.weekly_demand["week"].astype(int) == int(week)
        ]

    def _log_production(
        self,
        week: int,
        product_id: str,
        product_name: str,
        demand_quantity: float,
        planned_quantity: float,
        produced_quantity: float,
        production_time_hours: float,
        setup_time_minutes: float,
        status: str,
    ) -> None:
        self.production_log.append(
            {
                "week": week,
                "product_id": product_id,
                "product_name": product_name,
                "demand_quantity": demand_quantity,
                "planned_quantity": planned_quantity,
                "produced_quantity": produced_quantity,
                "production_time_hours": production_time_hours,
                "setup_time_minutes": setup_time_minutes,
                "status": status,
            }
        )

    def production_log_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.production_log)