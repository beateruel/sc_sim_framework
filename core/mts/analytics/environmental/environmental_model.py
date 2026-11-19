"""
Activity-based transport emissions for the MTS case (GLEC-style, tonne-km).

Scope covered by default: Scope 3 transport emissions
  * Inbound: raw-material purchases, quantity (t) x supplier distance (km)
    x emission factor of the delivery mode (gCO2e/tkm).
  * Outbound: one trip per week with shipments to the client,
    trip distance (km) x trip load (t) x emission factor (gCO2e/tkm).
    The trip is accounted at its nominal load (full-vehicle trip), so the
    outbound term depends on the number of trips and not on the shipped volume.
  * Production energy (Scope 2): production hours x energy rate (kWh/h)
    x grid carbon intensity (gCO2e/kWh). It is 0 by default.

All results are expressed in kg CO2e.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _load_supplier_transport(suppliers_file: Path) -> dict[str, dict]:
    with open(suppliers_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        str(int(float(s["supplier_id"]))): {
            "distance_km": float(s["distance_km"]),
            "mode": str(s.get("delivery_mode", "ROAD")).upper(),
        }
        for s in data.get("suppliers", [])
    }


def compute_mts_environmental_impact(
    purchase_orders_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
    production_df: pd.DataFrame,
    suppliers_file: Path,
    emissions_config: dict,
) -> pd.DataFrame:
    ef = {
        "ROAD": emissions_config["road_emission_factor_gco2_per_tkm"],
        "AIR": emissions_config["air_emission_factor_gco2_per_tkm"],
    }

    suppliers = _load_supplier_transport(suppliers_file)

    # ---- Inbound transport (g CO2e)
    inbound_g = 0.0
    if not purchase_orders_df.empty:
        for _, row in purchase_orders_df.iterrows():
            lane = suppliers[str(int(float(row["supplier_id"])))]
            tonnes = float(row["quantity"]) / 1000.0
            inbound_g += tonnes * lane["distance_km"] * ef[lane["mode"]]

    # ---- Outbound distribution (g CO2e): one trip per week with shipments
    trips = 0
    if not distribution_df.empty:
        shipped_by_week = distribution_df.groupby("week")["shipped_quantity"].sum()
        trips = int((shipped_by_week > 0).sum())

    client_mode = str(emissions_config.get("client_distribution_mode", "ROAD")).upper()
    emissions_per_trip_g = (
        emissions_config["client_distance_km"]
        * emissions_config["client_trip_load_tonnes"]
        * ef[client_mode]
    )
    outbound_g = trips * emissions_per_trip_g

    # ---- Production energy (g CO2e), 0 by default
    production_hours = (
        production_df["production_time_hours"].sum()
        if "production_time_hours" in production_df.columns
        else 0.0
    )
    production_g = (
        production_hours
        * emissions_config.get("production_energy_kwh_per_h", 0.0)
        * emissions_config.get("grid_carbon_intensity_gco2_per_kwh", 0.0)
    )

    inbound = inbound_g / 1000.0
    outbound = outbound_g / 1000.0
    production = production_g / 1000.0

    return pd.DataFrame(
        [
            {
                "inbound_transport_emissions_kgco2": inbound,
                "outbound_distribution_emissions_kgco2": outbound,
                "production_emissions_kgco2": production,
                "total_emissions_kgco2": inbound + outbound + production,
                "outbound_trips": trips,
            }
        ]
    )