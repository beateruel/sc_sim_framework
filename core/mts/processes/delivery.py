# core/mts/processes/deliver.py

from __future__ import annotations

import pandas as pd

from core.mts.entities.inventory import InventoryManager


class MTSDeliverProcess:
    def __init__(
        self,
        inventory: InventoryManager,
        weekly_demand: pd.DataFrame,
        product_price: float = 0.1,
        client_transport_time_hours: float = 24.0,
        client_storage_time_hours: float = 24.0,
        client_distribution_cost: float = 100.0,
        client_distribution_emissions: float = 100.0,
    ) -> None:
        self.inventory = inventory
        self.weekly_demand = weekly_demand

        self.product_price = product_price
        self.client_transport_time_hours = client_transport_time_hours
        self.client_storage_time_hours = client_storage_time_hours
        self.client_distribution_cost = client_distribution_cost
        self.client_distribution_emissions = client_distribution_emissions

        self.distribution_log: list[dict] = []

        self.total_distribution_cost = 0.0
        self.total_distribution_emissions = 0.0
        self.total_income = 0.0

    def execute_week(self, week: int) -> None:
        weekly_demand = self._get_demand_for_week(week)

        if weekly_demand.empty:
            return

        distribution_time_hours = (
            self.client_transport_time_hours
            + self.client_storage_time_hours
        )

        for _, demand_row in weekly_demand.iterrows():
            product_id = str(demand_row["product_id"])
            product_name = str(demand_row["product_name"])
            demand_quantity = float(demand_row["quantity_units"])

            shipped_quantity = self.inventory.ship_finished_good(
                product_id=product_id,
                quantity=demand_quantity,
                week=week,
                allow_partial=True,
            )

            income = shipped_quantity * self.product_price
            self.total_income += income

            self.distribution_log.append(
                {
                    "week": week,
                    "product_id": product_id,
                    "product_name": product_name,
                    "requested_quantity": demand_quantity,
                    "shipped_quantity": shipped_quantity,
                    "unfilled_quantity": demand_quantity - shipped_quantity,
                    "income": income,
                    "distribution_time_hours": distribution_time_hours,
                }
            )

        self.total_distribution_cost += self.client_distribution_cost
        self.total_distribution_emissions += self.client_distribution_emissions

    def _get_demand_for_week(self, week: int) -> pd.DataFrame:
        return self.weekly_demand[
            self.weekly_demand["week"].astype(int) == int(week)
        ]

    def distribution_log_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.distribution_log)