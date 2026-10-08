# core/mts/entities/inventory.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class DistributorRelease:
    """
    Release from ITI/distributor inventory to OHI/plant inventory.

    In this MTS logic:
    - ITI increases when a supplier purchase is launched/registered.
    - ITI decreases every release cycle, e.g. every 4 weeks.
    - OHI increases with that release at the beginning of the release week.
    """

    material_id: str
    quantity: float
    release_week: int


class InventoryManager:
    """
    Inventory manager for MTS simulations.

    Tracks:
    - OHI: on-hand raw material inventory at the plant
    - ITI: inventory in transit / distributor inventory / pipeline inventory
    - FI: finished goods inventory
    """

    def __init__(self) -> None:
        self.raw_material_oh: Dict[str, float] = {}
        self.raw_material_it: Dict[str, float] = {}
        self.finished_goods: Dict[str, float] = {}

        self.pending_distributor_releases: List[DistributorRelease] = []

        self.stockouts: Dict[int, int] = {}
        self.raw_material_shortages: Dict[int, Dict[str, float]] = {}
        self.finished_goods_shortages: Dict[int, Dict[str, float]] = {}

        self.inventory_history: List[dict] = []

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_raw_material(
        self,
        material_id: str,
        oh_quantity: float = 0.0,
        it_quantity: float = 0.0,
    ) -> None:
        material_id = str(material_id)
        self.raw_material_oh[material_id] = float(oh_quantity)
        self.raw_material_it[material_id] = float(it_quantity)

    def initialize_finished_good(
        self,
        product_id: str,
        quantity: float = 0.0,
    ) -> None:
        self.finished_goods[str(product_id)] = float(quantity)

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    def get_raw_material_oh(self, material_id: str) -> float:
        return self.raw_material_oh.get(str(material_id), 0.0)

    def get_raw_material_it(self, material_id: str) -> float:
        return self.raw_material_it.get(str(material_id), 0.0)

    def get_finished_good(self, product_id: str) -> float:
        return self.finished_goods.get(str(product_id), 0.0)

    # ------------------------------------------------------------------
    # ITI / distributor inventory
    # ------------------------------------------------------------------

    def add_to_iti(
        self,
        material_id: str,
        quantity: float,
    ) -> None:
        material_id = str(material_id)
        quantity = float(quantity)

        if quantity < 0:
            raise ValueError("Quantity added to ITI cannot be negative.")

        self.raw_material_it[material_id] = (
            self.get_raw_material_it(material_id) + quantity
        )

    def schedule_distributor_release(
        self,
        material_id: str,
        quantity: float,
        release_week: int,
    ) -> None:
        quantity = float(quantity)

        if quantity < 0:
            raise ValueError("Release quantity cannot be negative.")

        self.pending_distributor_releases.append(
            DistributorRelease(
                material_id=str(material_id),
                quantity=quantity,
                release_week=int(release_week),
            )
        )

    def process_distributor_releases(self, week: int) -> List[DistributorRelease]:
        """
        Moves material from ITI to OHI at the beginning of the release week.

        ITI decreases.
        OHI increases.
        """

        week = int(week)

        releases = [
            release
            for release in self.pending_distributor_releases
            if release.release_week == week
        ]

        processed: List[DistributorRelease] = []

        for release in releases:
            available_iti = self.get_raw_material_it(release.material_id)
            released_quantity = min(available_iti, release.quantity)

            self.raw_material_it[release.material_id] = (
                available_iti - released_quantity
            )

            self.raw_material_oh[release.material_id] = (
                self.get_raw_material_oh(release.material_id) + released_quantity
            )

            processed.append(
                DistributorRelease(
                    material_id=release.material_id,
                    quantity=released_quantity,
                    release_week=release.release_week,
                )
            )

        self.pending_distributor_releases = [
            release
            for release in self.pending_distributor_releases
            if release.release_week != week
        ]

        return processed

    # ------------------------------------------------------------------
    # OHI / plant raw material inventory
    # ------------------------------------------------------------------

    def consume_raw_material(
        self,
        material_id: str,
        quantity: float,
        week: int,
        allow_partial: bool = False,
    ) -> float:
        material_id = str(material_id)
        quantity = float(quantity)

        if quantity < 0:
            raise ValueError("Consumed quantity cannot be negative.")

        available = self.get_raw_material_oh(material_id)

        if available >= quantity:
            self.raw_material_oh[material_id] = available - quantity
            return quantity

        shortage = quantity - available
        self._register_raw_material_shortage(
            week=week,
            material_id=material_id,
            shortage=shortage,
        )
        self.stockouts[int(week)] = 1

        if not allow_partial:
            return 0.0

        self.raw_material_oh[material_id] = 0.0
        return available

    # ------------------------------------------------------------------
    # Finished goods inventory
    # ------------------------------------------------------------------

    def add_finished_good(
        self,
        product_id: str,
        quantity: float,
    ) -> None:
        product_id = str(product_id)
        quantity = float(quantity)

        if quantity < 0:
            raise ValueError("Finished goods quantity cannot be negative.")

        self.finished_goods[product_id] = (
            self.get_finished_good(product_id) + quantity
        )

    def ship_finished_good(
        self,
        product_id: str,
        quantity: float,
        week: int,
        allow_partial: bool = True,
    ) -> float:
        product_id = str(product_id)
        quantity = float(quantity)

        if quantity < 0:
            raise ValueError("Shipped quantity cannot be negative.")

        available = self.get_finished_good(product_id)

        if available >= quantity:
            self.finished_goods[product_id] = available - quantity
            return quantity

        shortage = quantity - available
        self._register_finished_goods_shortage(
            week=week,
            product_id=product_id,
            shortage=shortage,
        )
        self.stockouts[int(week)] = 1

        if not allow_partial:
            return 0.0

        self.finished_goods[product_id] = 0.0
        return available

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------

    def get_raw_material_inventory_position(self, material_id: str) -> float:
        material_id = str(material_id)
        return (
            self.get_raw_material_oh(material_id)
            + self.get_raw_material_it(material_id)
        )

    def get_total_raw_material_oh(self) -> float:
        return sum(self.raw_material_oh.values())

    def get_total_raw_material_it(self) -> float:
        return sum(self.raw_material_it.values())

    def get_total_finished_goods(self) -> float:
        return sum(self.finished_goods.values())

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def record_week(self, week: int) -> None:
        week = int(week)

        material_ids = sorted(
            set(self.raw_material_oh.keys()) | set(self.raw_material_it.keys())
        )
        product_ids = sorted(self.finished_goods.keys())

        record = {
            "week": week,
            "total_raw_material_oh": self.get_total_raw_material_oh(),
            "total_raw_material_it": self.get_total_raw_material_it(),
            "total_finished_goods": self.get_total_finished_goods(),
            "stockout": self.stockouts.get(week, 0),
        }

        for material_id in material_ids:
            record[f"raw_material_oh_{material_id}"] = (
                self.get_raw_material_oh(material_id)
            )
            record[f"raw_material_it_{material_id}"] = (
                self.get_raw_material_it(material_id)
            )

        for product_id in product_ids:
            record[f"finished_goods_{product_id}"] = (
                self.get_finished_good(product_id)
            )

        self.inventory_history.append(record)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.inventory_history)

    # ------------------------------------------------------------------
    # Shortage tracking
    # ------------------------------------------------------------------

    def _register_raw_material_shortage(
        self,
        week: int,
        material_id: str,
        shortage: float,
    ) -> None:
        week = int(week)
        material_id = str(material_id)

        self.raw_material_shortages.setdefault(week, {})
        self.raw_material_shortages[week][material_id] = (
            self.raw_material_shortages[week].get(material_id, 0.0)
            + float(shortage)
        )

    def _register_finished_goods_shortage(
        self,
        week: int,
        product_id: str,
        shortage: float,
    ) -> None:
        week = int(week)
        product_id = str(product_id)

        self.finished_goods_shortages.setdefault(week, {})
        self.finished_goods_shortages[week][product_id] = (
            self.finished_goods_shortages[week].get(product_id, 0.0)
            + float(shortage)
        )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.raw_material_oh.clear()
        self.raw_material_it.clear()
        self.finished_goods.clear()
        self.pending_distributor_releases.clear()
        self.stockouts.clear()
        self.raw_material_shortages.clear()
        self.finished_goods_shortages.clear()
        self.inventory_history.clear()