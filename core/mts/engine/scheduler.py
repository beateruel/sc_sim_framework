# core/mts/engine/scheduler.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from core.mts.entities.inventory import InventoryManager
from core.mts.processes.source import MTSSourcingProcess
from core.mts.processes.make import MTSMakeProcess
from core.mts.processes.delivery import MTSDeliverProcess


@dataclass
class MTSConfig:
    labour_cost_per_hour: float = 17.0
    ordering_cost: float = 100.0
    holding_rate: float = 0.2
    product_price: float = 0.1

    client_transport_time_hours: float = 24.0
    client_storage_time_hours: float = 24.0
    client_distribution_cost: float = 100.0
    client_distribution_emissions: float = 100.0

    weeks_per_month: int = 4
    purchase_cycle_weeks: int = 12
    demand_coverage_weeks: int = 12
    distributor_release_cycle_weeks: int = 4


class MTSStrategy:
    def __init__(
        self,
        inventory: InventoryManager,
        weekly_demand: pd.DataFrame,
        planning_demand: Optional[pd.DataFrame] = None,
        products_bom: pd.DataFrame = None,
        suppliers: pd.DataFrame = None,
        material_prices: Optional[dict] = None,
        config: Optional[MTSConfig] = None,
        shortage_start_week: int = -1,
        shortage_end_week: int = -1,
    ) -> None:

        self.inventory = inventory

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

        self.shortage_start_week = shortage_start_week
        self.shortage_end_week = shortage_end_week

        self.sourcing = MTSSourcingProcess(
            inventory=self.inventory,
            weekly_demand=self.planning_demand,
            products_bom=self.products_bom,
            suppliers=self.suppliers,
            material_prices=self.material_prices,
            weeks_per_month=self.config.weeks_per_month,
            purchase_cycle_weeks=self.config.purchase_cycle_weeks,
            demand_coverage_weeks=self.config.demand_coverage_weeks,
            release_cycle_weeks=self.config.distributor_release_cycle_weeks,
            ordering_cost=self.config.ordering_cost,
            shortage_start_week=self.shortage_start_week,
            shortage_end_week=self.shortage_end_week,
        )

        self.make = MTSMakeProcess(
            inventory=self.inventory,
            weekly_demand=self.planning_demand,
            products_bom=self.products_bom,
            labour_cost_per_hour=self.config.labour_cost_per_hour,
        )

        self.deliver = MTSDeliverProcess(
            inventory=self.inventory,
            weekly_demand=self.weekly_demand,
            product_price=self.config.product_price,
            client_transport_time_hours=self.config.client_transport_time_hours,
            client_storage_time_hours=self.config.client_storage_time_hours,
            client_distribution_cost=self.config.client_distribution_cost,
            client_distribution_emissions=self.config.client_distribution_emissions,
        )

        self.weekly_metrics: list[dict] = []

    def execute_week(self, week: int) -> None:
        week = int(week)

        self.sourcing.execute_week(week)
        self.deliver.execute_week(week) #deliver the demand with the existing stock
        self.make.execute_week(week)    #make the products to replenish the stock
       

        self.inventory.record_week(week)
        self._record_weekly_metrics(week)

    def _record_weekly_metrics(self, week: int) -> None:
        self.weekly_metrics.append(
            {
                "week": week,
                "total_purchase_cost": self.sourcing.total_purchase_cost,
                "total_ordering_cost": self.sourcing.total_ordering_cost,
                "total_production_cost": self.make.total_production_cost,
                "total_distribution_cost": self.deliver.total_distribution_cost,
                "total_distribution_emissions": self.deliver.total_distribution_emissions,
                "total_income": self.deliver.total_income,
                "stockout": self.inventory.stockouts.get(week, 0),
            }
        )

    def purchase_orders_to_dataframe(self) -> pd.DataFrame:
        return self.sourcing.purchase_orders_to_dataframe()

    def releases_to_dataframe(self) -> pd.DataFrame:
        return self.sourcing.releases_to_dataframe()

    def production_log_to_dataframe(self) -> pd.DataFrame:
        return self.make.production_log_to_dataframe()

    def distribution_log_to_dataframe(self) -> pd.DataFrame:
        return self.deliver.distribution_log_to_dataframe()

    def arrivals_to_dataframe(self) -> pd.DataFrame:
        return self.releases_to_dataframe()

    def weekly_metrics_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.weekly_metrics)

    def summary(self) -> dict:
        total_cost = (
            self.sourcing.total_purchase_cost
            + self.sourcing.total_ordering_cost
            + self.make.total_production_cost
            + self.deliver.total_distribution_cost
        )

        return {
            "total_purchase_cost": self.sourcing.total_purchase_cost,
            "total_ordering_cost": self.sourcing.total_ordering_cost,
            "total_production_cost": self.make.total_production_cost,
            "total_distribution_cost": self.deliver.total_distribution_cost,
            "total_distribution_emissions": self.deliver.total_distribution_emissions,
            "total_income": self.deliver.total_income,
            "total_cost": total_cost,
            "total_profit": self.deliver.total_income - total_cost,
        }