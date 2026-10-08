# core/mts/processes/source.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from core.mts.entities.inventory import InventoryManager


@dataclass
class PurchaseOrder:
    week: int
    material_id: str
    supplier_id: str
    quantity: float
    unit_price: float
    purchase_cost: float
    ordering_cost: float


class MTSSourcingProcess:
    def __init__(
        self,
        inventory: InventoryManager,
        weekly_demand: pd.DataFrame,
        products_bom: pd.DataFrame,
        suppliers: pd.DataFrame,
        material_prices: Optional[dict] = None,
        weeks_per_month: int = 4,
        purchase_cycle_weeks: int = 12,
        demand_coverage_weeks: int = 12,
        release_cycle_weeks: int = 4,
        ordering_cost: float = 100.0,
        shortage_start_week: int = -1,
        shortage_end_week: int = -1,
    ) -> None:
        self.inventory = inventory
        self.weekly_demand = weekly_demand
        self.products_bom = products_bom
        self.suppliers = suppliers
        self.material_prices = material_prices or {}

        self.weeks_per_month = weeks_per_month
        self.purchase_cycle_weeks = purchase_cycle_weeks
        self.demand_coverage_weeks = demand_coverage_weeks
        self.release_cycle_weeks = release_cycle_weeks
        self.ordering_cost = ordering_cost

        self.shortage_start_week = shortage_start_week
        self.shortage_end_week = shortage_end_week

        self.purchase_orders: list[PurchaseOrder] = []
        self.release_log: list[dict] = []

        self.total_purchase_cost = 0.0
        self.total_ordering_cost = 0.0

    def execute_week(self, week: int) -> None:
        week = int(week)

        self._launch_purchase_if_due(week)

        releases = self.inventory.process_distributor_releases(week)

        for release in releases:
            self.release_log.append(
                {
                    "week": week,
                    "material_id": release.material_id,
                    "quantity": release.quantity,
                }
            )

    def _launch_purchase_if_due(self, week: int) -> None:
        if self._is_supply_interrupted(week):
            return

        if week % self.purchase_cycle_weeks != 0:
            return

        for _, supplier in self.suppliers.iterrows():
            material_id = str(supplier["material_id"])
            supplier_id = str(supplier["supplier_id"])

            quantity = self._calculate_purchase_quantity(
                material_id=material_id,
                start_week=week,
                coverage_weeks=self.demand_coverage_weeks,
                supplier=supplier,
            )

            if quantity <= 0:
                continue

            unit_price = self._get_material_price(week)

            self.inventory.add_to_iti(
                material_id=material_id,
                quantity=quantity,
            )

            lead_time_weeks = int(
                supplier.get("lead_time_weeks", 0)
            )

            self._schedule_releases_for_purchase(
                material_id=material_id,
                purchase_week=week,
                coverage_weeks=self.demand_coverage_weeks,
                release_cycle_weeks=self.release_cycle_weeks,
                lead_time_weeks=lead_time_weeks,
            )

            purchase_order = PurchaseOrder(
                week=week,
                material_id=material_id,
                supplier_id=supplier_id,
                quantity=quantity,
                unit_price=unit_price,
                purchase_cost=quantity * unit_price,
                ordering_cost=self.ordering_cost,
            )

            self.purchase_orders.append(purchase_order)
            self.total_purchase_cost += purchase_order.purchase_cost
            self.total_ordering_cost += purchase_order.ordering_cost

    def _is_supply_interrupted(self, week: int) -> bool:
        return (
            self.shortage_start_week >= 0
            and self.shortage_end_week >= 0
            and self.shortage_start_week <= week < self.shortage_end_week
        )

    def _calculate_purchase_quantity(
        self,
        material_id: str,
        start_week: int,
        coverage_weeks: int,
        supplier: pd.Series,
    ) -> float:
        total_quantity = 0.0

        for future_week in range(
            start_week,
            start_week + coverage_weeks,
        ):
            total_quantity += self._calculate_material_required_for_week(
                material_id=material_id,
                week=future_week,
            )

        minimum_reorder_quantity = float(
            supplier.get("reorder_quantity_kg", 0.0)
        )

        return max(total_quantity, minimum_reorder_quantity)

    def _schedule_releases_for_purchase(
        self,
        material_id: str,
        purchase_week: int,
        coverage_weeks: int,
        release_cycle_weeks: int,
        lead_time_weeks: int,
    ) -> None:
        for offset in range(
            0,
            coverage_weeks,
            release_cycle_weeks,
        ):
            release_week = (
                purchase_week
                + lead_time_weeks
                + offset
            )

            quantity = 0.0

            for future_week in range(
                purchase_week + offset,
                purchase_week + offset + release_cycle_weeks,
            ):
                quantity += self._calculate_material_required_for_week(
                    material_id=material_id,
                    week=future_week,
                )

            self.inventory.schedule_distributor_release(
                material_id=material_id,
                quantity=quantity,
                release_week=release_week,
            )

    def _calculate_material_required_for_week(
        self,
        material_id: str,
        week: int,
    ) -> float:
        weekly_demand = self.weekly_demand[
            self.weekly_demand["week"].astype(int) == int(week)
        ]

        if weekly_demand.empty:
            return 0.0

        required_quantity = 0.0

        for _, demand_row in weekly_demand.iterrows():
            product_id = str(demand_row["product_id"])
            demand_quantity = float(demand_row["quantity_units"])

            material_rows = self.products_bom[
                (
                    self.products_bom["product_id"].astype(str)
                    == product_id
                )
                & (
                    self.products_bom["material_id"].astype(str)
                    == str(material_id)
                )
            ]

            if material_rows.empty:
                continue

            material_weight_g = float(
                material_rows.iloc[0][
                    "material_quantity_g_per_unit"
                ]
            )

            required_quantity += (
                demand_quantity
                * material_weight_g
                / 1000.0
            )

        return required_quantity

    def _get_material_price(self, week: int) -> float:
        month_index = int(week // self.weeks_per_month)

        if month_index in self.material_prices:
            return float(self.material_prices[month_index])

        if str(month_index) in self.material_prices:
            return float(self.material_prices[str(month_index)])

        return 0.0

    def purchase_orders_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [po.__dict__ for po in self.purchase_orders]
        )

    def releases_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.release_log)