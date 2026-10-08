# core/mts/analytics/environmental/environmental_model.py

from __future__ import annotations

import pandas as pd


def compute_mts_environmental_impact(
    purchase_orders_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
    production_df: pd.DataFrame,
    road_emission_factor: float = 74,
    electricity_emission_factor: float = 245,
    shopfloor_energy_rate: float = 0.36,
) -> pd.DataFrame:
    total_purchased_quantity = (
        purchase_orders_df["quantity"].sum()
        if "quantity" in purchase_orders_df.columns
        else 0
    )

    inbound_transport_emissions = (
        total_purchased_quantity * road_emission_factor / 1000
    )

    outbound_distribution_emissions = (
        distribution_df["distribution_time_hours"].sum() * road_emission_factor
        if "distribution_time_hours" in distribution_df.columns
        else 0
    )

    total_production_hours = (
        production_df["production_time_hours"].sum()
        if "production_time_hours" in production_df.columns
        else 0
    )

    production_energy_consumption = total_production_hours * shopfloor_energy_rate

    production_emissions = (
        production_energy_consumption * electricity_emission_factor / 1000
    )

    total_emissions = (
        inbound_transport_emissions
        + outbound_distribution_emissions
        + production_emissions
    )

    return pd.DataFrame(
        [
            {
                "inbound_transport_emissions_kgco2": inbound_transport_emissions,
                "outbound_distribution_emissions_kgco2": outbound_distribution_emissions,
                "production_emissions_kgco2": production_emissions,
                "total_emissions_kgco2": total_emissions,
            }
        ]
    )