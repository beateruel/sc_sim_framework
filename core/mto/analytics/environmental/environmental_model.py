import pandas as pd


def compute_environmental_impact(orders, config):
    rows = []

    for o in orders:
        is_digital = (
            hasattr(o, "prototyping_type")
            and str(o.prototyping_type).upper() == "DIGITAL"
        )

        sample_units = 0 if is_digital else o.sample_units

        material_per_piece = o.material_per_piece

        # ==============================
        # SAMPLE MATERIAL / TRANSPORT
        # ==============================
        tons_sample = (sample_units * material_per_piece) / 1000

        supplier_sample = o.data["supplier_sample"]

        distance_sample = supplier_sample["distance"]
        mode_sample = supplier_sample["material_reception_mode_of_transport"]

        if mode_sample == "AIR":
            factor_sample = config["environmental"]["air_emission_factor_gco2_per_tkm"]
        else:
            factor_sample = config["environmental"]["road_emission_factor_gco2_per_tkm"]

        sample_transport_CO2 = tons_sample * distance_sample * factor_sample

        # ==============================
        # PRODUCTION MATERIAL / TRANSPORT
        # ==============================
        units = o.production_units
        tons_production = (units * material_per_piece) / 1000

        supplier = o.data["supplier_material"]

        distance_material = supplier["distance"]
        mode_material = supplier["material_reception_mode_of_transport"]

        if mode_material == "AIR":
            factor_material = config["environmental"]["air_emission_factor_gco2_per_tkm"]
        else:
            factor_material = config["environmental"]["road_emission_factor_gco2_per_tkm"]

        material_transport_CO2 = tons_production * distance_material * factor_material

        # ==============================
        # DISTRIBUTION
        # ==============================
        client = o.data["client"]

        distance_distribution = client["distance"]
        mode_distribution = client["fullfilment_distribution_mode_of_transport"]

        if mode_distribution == "AIR":
            factor_distribution = config["environmental"]["air_emission_factor_gco2_per_tkm"]
        else:
            factor_distribution = config["environmental"]["road_emission_factor_gco2_per_tkm"]

        distribution_CO2 = tons_production * distance_distribution * factor_distribution

        # ==============================
        # PRODUCTION EMISSIONS
        # ==============================
        production_CO2 = o.production_emissions

        # ==============================
        # TOTAL CO2
        # ==============================
        total_CO2 = (
            sample_transport_CO2
            + material_transport_CO2
            + distribution_CO2
            + production_CO2
        )

        # ==============================
        # WASTE
        # ==============================
        original_sample_units = o.sample_units

        total_material_input = (
            (o.production_units + sample_units)
            * material_per_piece
        )

        avoided_sample_waste = (
            original_sample_units * material_per_piece
            if is_digital
            else 0.0
        )

        effective_waste = max(
            0.0,
            o.waste - avoided_sample_waste
        )

        waste = (
            effective_waste / total_material_input
            if total_material_input > 0
            else 0.0
        )

        

        rows.append(
            {
                "order": o.id,
                "prototyping_type": getattr(o, "prototyping_type", None),
                "sample_units_accounted": sample_units,
                "sample_transport_CO2": sample_transport_CO2,
                "material_transport_CO2": material_transport_CO2,
                "distribution_CO2": distribution_CO2,
                "production_CO2": production_CO2,
                "total_CO2": total_CO2,
                "waste": waste
            }
        )

    return pd.DataFrame(rows)