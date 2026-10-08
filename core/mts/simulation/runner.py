from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from core.mts.entities.inventory import InventoryManager
from core.mts.engine.scheduler import MTSConfig, MTSStrategy


class MTSSimulationRunner:
    def __init__(
        self,
        weekly_demand: pd.DataFrame,
        products_bom: pd.DataFrame,
        suppliers: pd.DataFrame,
        material_prices: Optional[dict] = None,
        config: Optional[MTSConfig] = None,
        simulation_weeks: Optional[int] = None,
        shortage_start_week: int = -1,
        shortage_end_week: int = -1,
        initial_raw_material_inventory: Optional[dict] = None,
        initial_finished_goods_inventory: Optional[dict] = None,
        planning_demand: Optional[pd.DataFrame] = None,
    ) -> None:

        self.weekly_demand = weekly_demand

        self.planning_demand = (
            planning_demand
            if planning_demand is not None
            else weekly_demand
        )

        self.products_bom = products_bom
        self.suppliers = suppliers
        self.material_prices = material_prices or {}
        self.config = config or MTSConfig()

        self.initial_raw_material_inventory = (
            initial_raw_material_inventory or {}
        )

        self.initial_finished_goods_inventory = (
            initial_finished_goods_inventory or {}
        )

        self.simulation_weeks = (
            int(simulation_weeks)
            if simulation_weeks is not None
            else int(self.weekly_demand["week"].max()) + 1
        )

        self.inventory = InventoryManager()

        self._initialize_inventory()

        self.strategy = MTSStrategy(
            inventory=self.inventory,
            weekly_demand=self.weekly_demand,
            planning_demand=self.planning_demand,
            products_bom=self.products_bom,
            suppliers=self.suppliers,
            material_prices=self.material_prices,
            config=self.config,
            shortage_start_week=shortage_start_week,
            shortage_end_week=shortage_end_week,
        )

    def _initialize_inventory(self) -> None:
        for material_id in (
            self.products_bom["material_id"]
            .astype(str)
            .unique()
        ):
            quantity = self.initial_raw_material_inventory.get(
                material_id,
                0.0,
            )

            self.inventory.initialize_raw_material(
                material_id=material_id,
                oh_quantity=quantity,
                it_quantity=0.0,
            )

        for product_id in (
            self.products_bom["product_id"]
            .astype(str)
            .unique()
        ):
            quantity = self.initial_finished_goods_inventory.get(
                product_id,
                0.0,
            )

            self.inventory.initialize_finished_good(
                product_id=product_id,
                quantity=quantity,
            )

    def run(self) -> dict:
        for week in range(self.simulation_weeks):
            self.strategy.execute_week(week)

        return self.strategy.summary()

    def get_results(self) -> dict:
        return {
            "summary": self.strategy.summary(),
            "inventory": self.inventory.to_dataframe(),
            "purchase_orders": self.strategy.purchase_orders_to_dataframe(),
            "releases": self.strategy.releases_to_dataframe(),
            "production": self.strategy.production_log_to_dataframe(),
            "distribution": self.strategy.distribution_log_to_dataframe(),
            "arrivals": self.strategy.arrivals_to_dataframe(),
            "weekly_metrics": self.strategy.weekly_metrics_to_dataframe(),
        }

    def save_results(
        self,
        output_dir: str | Path,
    ) -> None:

        output_dir = Path(output_dir)

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        results = self.get_results()

        for name, data in results.items():

            if name == "summary":

                pd.DataFrame([data]).to_csv(
                    output_dir / "summary.csv",
                    index=False,
                )

            else:

                data.to_csv(
                    output_dir / f"{name}.csv",
                    index=False,
                )