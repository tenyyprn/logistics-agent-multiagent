"""
Cost Calculation Tools for Logistics Agent
費用計算ツール
"""

import json
import os
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_rates_data() -> dict:
    """料金データを読み込む"""
    rates_file = os.path.join(DATA_DIR, "rates.json")
    if os.path.exists(rates_file):
        with open(rates_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def calculate_sea_freight_cost(
    origin_country: str,
    destination_country: str,
    cargo_weight_kg: float,
    cargo_volume_cbm: float,
    container_type: str = "LCL"
) -> dict:
    """
    Calculate sea freight cost for a shipment.
    海上輸送の費用を計算します。

    Args:
        origin_country: Origin country (e.g., "Japan")
        destination_country: Destination country (e.g., "China")
        cargo_weight_kg: Cargo weight in kilograms
        cargo_volume_cbm: Cargo volume in cubic meters
        container_type: "LCL", "20ft", "40ft", or "40ft_HC"

    Returns:
        dict: Detailed cost breakdown in USD
    """
    rates = load_rates_data()
    sea_rates = rates.get("sea_freight_rates", {})
    
    # Determine lane
    lane = f"{origin_country}-{destination_country}"
    base_rates = sea_rates.get("base_rates_per_cbm", {}).get(lane)
    
    if not base_rates:
        # Try reverse mapping for common routes
        lane_mapping = {
            "Japan-China": ["Japan-China"],
            "Japan-Thailand": ["Japan-Thailand"],
            "Japan-USA": ["Japan-USA"],
            "Japan-Europe": ["Japan-Europe"],
        }
        for key in lane_mapping:
            if origin_country in key and destination_country.lower() in key.lower():
                base_rates = sea_rates.get("base_rates_per_cbm", {}).get(key)
                break
    
    if not base_rates:
        return {
            "status": "error",
            "message": f"No rates available for {lane}. Please contact sales for a custom quote."
        }
    
    surcharges = sea_rates.get("surcharges", {})
    
    # Calculate base freight
    if container_type == "LCL":
        # LCL charged by CBM or weight (1 CBM = 1000 kg), whichever is greater
        chargeable_cbm = max(cargo_volume_cbm, cargo_weight_kg / 1000)
        base_freight = chargeable_cbm * base_rates.get("LCL", 50)
        container_info = f"LCL: {chargeable_cbm:.2f} CBM chargeable"
    else:
        base_freight = base_rates.get(container_type, base_rates.get("20ft", 200))
        container_info = f"{container_type} Container"
    
    # Calculate surcharges
    baf = base_freight * surcharges.get("BAF", {}).get("rate_percent", 15) / 100
    caf = base_freight * surcharges.get("CAF", {}).get("rate_percent", 5) / 100
    thc_origin = surcharges.get("THC_origin", {}).get("rate_usd", 150)
    thc_dest = surcharges.get("THC_destination", {}).get("rate_usd", 180)
    doc_fee = surcharges.get("documentation_fee", {}).get("rate_usd", 50)
    seal_fee = surcharges.get("seal_fee", {}).get("rate_usd", 15) if container_type != "LCL" else 0
    
    # Total calculation
    total_freight = base_freight + baf + caf
    total_charges = thc_origin + thc_dest + doc_fee + seal_fee
    grand_total = total_freight + total_charges
    
    return {
        "status": "success",
        "transport_mode": "Sea Freight",
        "container_type": container_info,
        "route": lane,
        "cargo": {
            "weight_kg": cargo_weight_kg,
            "volume_cbm": cargo_volume_cbm
        },
        "cost_breakdown": {
            "base_freight": round(base_freight, 2),
            "BAF_bunker_adjustment": round(baf, 2),
            "CAF_currency_adjustment": round(caf, 2),
            "THC_origin": thc_origin,
            "THC_destination": thc_dest,
            "documentation_fee": doc_fee,
            "seal_fee": seal_fee
        },
        "subtotals": {
            "freight_total": round(total_freight, 2),
            "charges_total": total_charges
        },
        "grand_total_usd": round(grand_total, 2),
        "currency": "USD",
        "validity": "30 days from quote date",
        "notes": ["Rates subject to space availability", "Actual charges may vary based on final measurement"]
    }


def calculate_air_freight_cost(
    origin_country: str,
    destination_country: str,
    cargo_weight_kg: float,
    cargo_volume_cbm: float,
    cargo_value_usd: Optional[float] = None
) -> dict:
    """
    Calculate air freight cost for a shipment.
    航空輸送の費用を計算します。

    Args:
        origin_country: Origin country
        destination_country: Destination country
        cargo_weight_kg: Actual cargo weight in kilograms
        cargo_volume_cbm: Cargo volume in cubic meters
        cargo_value_usd: Optional cargo value for insurance calculation

    Returns:
        dict: Detailed cost breakdown in USD
    """
    rates = load_rates_data()
    air_rates = rates.get("air_freight_rates", {})
    
    # Determine lane
    lane = f"{origin_country}-{destination_country}"
    base_rates = air_rates.get("base_rates_per_kg", {}).get(lane)
    
    if not base_rates:
        for key in air_rates.get("base_rates_per_kg", {}).keys():
            if origin_country in key and destination_country.lower() in key.lower():
                base_rates = air_rates.get("base_rates_per_kg", {}).get(key)
                break
    
    if not base_rates:
        return {
            "status": "error",
            "message": f"No air freight rates available for {lane}."
        }
    
    surcharges = air_rates.get("surcharges", {})
    dim_factor = air_rates.get("dimensional_factor", 6000)
    
    # Calculate volumetric weight
    volumetric_weight = cargo_volume_cbm * 1000000 / dim_factor  # CBM to cm³ to kg
    chargeable_weight = max(cargo_weight_kg, volumetric_weight)
    
    # Determine rate tier
    if chargeable_weight < 45:
        rate_per_kg = base_rates.get("under_45kg", 10)
    elif chargeable_weight < 100:
        rate_per_kg = base_rates.get("45_100kg", 8)
    elif chargeable_weight < 300:
        rate_per_kg = base_rates.get("100_300kg", 6)
    elif chargeable_weight < 500:
        rate_per_kg = base_rates.get("300_500kg", 5)
    else:
        rate_per_kg = base_rates.get("over_500kg", 4)
    
    # Calculate costs
    base_freight = max(chargeable_weight * rate_per_kg, base_rates.get("min_charge", 80))
    fuel_surcharge = base_freight * surcharges.get("fuel_surcharge_percent", 25) / 100
    security_fee = chargeable_weight * surcharges.get("security_surcharge_per_kg", 0.15)
    awb_fee = surcharges.get("AWB_fee", 30)
    handling_fee = chargeable_weight * surcharges.get("handling_fee_per_kg", 0.25)
    
    total_freight = base_freight + fuel_surcharge + security_fee
    total_charges = awb_fee + handling_fee
    grand_total = total_freight + total_charges
    
    return {
        "status": "success",
        "transport_mode": "Air Freight",
        "route": lane,
        "weight_calculation": {
            "actual_weight_kg": cargo_weight_kg,
            "volumetric_weight_kg": round(volumetric_weight, 2),
            "chargeable_weight_kg": round(chargeable_weight, 2),
            "rate_per_kg": rate_per_kg
        },
        "cost_breakdown": {
            "base_freight": round(base_freight, 2),
            "fuel_surcharge": round(fuel_surcharge, 2),
            "security_fee": round(security_fee, 2),
            "AWB_fee": awb_fee,
            "handling_fee": round(handling_fee, 2)
        },
        "subtotals": {
            "freight_total": round(total_freight, 2),
            "charges_total": round(total_charges, 2)
        },
        "grand_total_usd": round(grand_total, 2),
        "currency": "USD",
        "validity": "7 days from quote date",
        "notes": ["Subject to space availability", "Dangerous goods may incur additional charges"]
    }


def calculate_total_landed_cost(
    freight_cost_usd: float,
    cargo_value_usd: float,
    destination_country: str,
    hs_code: str = "8479",
    include_insurance: bool = True
) -> dict:
    """
    Calculate total landed cost including customs duties and taxes.
    関税・税金を含む総着地費用を計算します。

    Args:
        freight_cost_usd: Total freight cost in USD
        cargo_value_usd: Commercial value of cargo in USD
        destination_country: Destination country
        hs_code: Harmonized System code for the goods
        include_insurance: Whether to include cargo insurance

    Returns:
        dict: Complete landed cost breakdown
    """
    rates = load_rates_data()
    customs_rates = rates.get("customs_clearance", {})
    insurance_rates = rates.get("insurance_rates", {})
    
    # Get customs clearance fees
    dest_key = f"{destination_country}_import"
    customs_fees = customs_rates.get(dest_key, customs_rates.get("China_import", {}))
    
    customs_doc = customs_fees.get("documentation", 65)
    customs_inspection = customs_fees.get("inspection", 100)
    customs_handling = customs_fees.get("handling", 55)
    total_customs_fees = customs_doc + customs_inspection + customs_handling
    
    # Estimate duties (simplified)
    duty_rates = {
        "8471": 0.03,  # Computers
        "8479": 0.05,  # Machinery
        "8501": 0.08,  # Motors
        "8517": 0.02,  # Communication equipment
    }
    duty_rate = duty_rates.get(hs_code[:4], 0.05)
    estimated_duty = cargo_value_usd * duty_rate
    
    # VAT (estimated)
    vat_rates = {"China": 0.13, "Thailand": 0.07, "USA": 0, "Europe": 0.20}
    vat_rate = vat_rates.get(destination_country, 0.10)
    vat_base = cargo_value_usd + estimated_duty
    estimated_vat = vat_base * vat_rate
    
    # Insurance
    insurance_cost = 0
    if include_insurance:
        insured_value = cargo_value_usd * 1.1  # CIF + 10%
        insurance_rate = insurance_rates.get("standard_percent", 0.35) / 100
        insurance_cost = max(insured_value * insurance_rate, insurance_rates.get("minimum_premium_usd", 25))
    
    # Calculate totals
    cif_value = cargo_value_usd + freight_cost_usd + insurance_cost
    total_duties_taxes = estimated_duty + estimated_vat
    total_landed_cost = cif_value + total_duties_taxes + total_customs_fees
    
    return {
        "status": "success",
        "destination": destination_country,
        "hs_code": hs_code,
        "value_breakdown": {
            "cargo_value_fob": cargo_value_usd,
            "freight_cost": freight_cost_usd,
            "insurance": round(insurance_cost, 2),
            "cif_value": round(cif_value, 2)
        },
        "duties_and_taxes": {
            "customs_duty": round(estimated_duty, 2),
            "duty_rate_percent": duty_rate * 100,
            "vat_tax": round(estimated_vat, 2),
            "vat_rate_percent": vat_rate * 100
        },
        "customs_clearance_fees": {
            "documentation": customs_doc,
            "inspection": customs_inspection,
            "handling": customs_handling,
            "total": total_customs_fees
        },
        "summary": {
            "cif_value": round(cif_value, 2),
            "total_duties_taxes": round(total_duties_taxes, 2),
            "customs_fees": total_customs_fees,
            "total_landed_cost_usd": round(total_landed_cost, 2)
        },
        "currency": "USD",
        "disclaimer": "Duty and tax estimates are approximate. Final amounts determined by customs authority."
    }


def compare_shipping_options(
    origin_country: str,
    destination_country: str,
    cargo_weight_kg: float,
    cargo_volume_cbm: float,
    cargo_value_usd: float
) -> dict:
    """
    Compare different shipping options and provide recommendations.
    複数の輸送オプションを比較し、推奨を提供します。

    Args:
        origin_country: Origin country
        destination_country: Destination country
        cargo_weight_kg: Cargo weight in kg
        cargo_volume_cbm: Cargo volume in CBM
        cargo_value_usd: Cargo value in USD

    Returns:
        dict: Comparison of all available options
    """
    options = []
    
    # Sea freight LCL
    sea_lcl = calculate_sea_freight_cost(
        origin_country, destination_country,
        cargo_weight_kg, cargo_volume_cbm, "LCL"
    )
    if sea_lcl["status"] == "success":
        options.append({
            "option": "Sea Freight (LCL)",
            "freight_cost": sea_lcl["grand_total_usd"],
            "transit_days": "5-14 days (varies by destination)",
            "best_for": "Cost-effective for smaller shipments"
        })
    
    # Sea freight FCL (if volume warrants)
    if cargo_volume_cbm >= 10:
        container = "20ft" if cargo_volume_cbm <= 25 else "40ft"
        sea_fcl = calculate_sea_freight_cost(
            origin_country, destination_country,
            cargo_weight_kg, cargo_volume_cbm, container
        )
        if sea_fcl["status"] == "success":
            options.append({
                "option": f"Sea Freight ({container} FCL)",
                "freight_cost": sea_fcl["grand_total_usd"],
                "transit_days": "5-14 days (varies by destination)",
                "best_for": "Large volume shipments, full container control"
            })
    
    # Air freight
    air = calculate_air_freight_cost(
        origin_country, destination_country,
        cargo_weight_kg, cargo_volume_cbm
    )
    if air["status"] == "success":
        options.append({
            "option": "Air Freight",
            "freight_cost": air["grand_total_usd"],
            "transit_days": "1-3 days",
            "best_for": "Urgent shipments, high-value goods"
        })
    
    # Sort by cost
    options.sort(key=lambda x: x["freight_cost"])
    
    # Add recommendation
    if options:
        cheapest = options[0]
        fastest = min(options, key=lambda x: 1 if "Air" in x["option"] else 10)
        
        return {
            "status": "success",
            "cargo_summary": {
                "weight_kg": cargo_weight_kg,
                "volume_cbm": cargo_volume_cbm,
                "value_usd": cargo_value_usd
            },
            "options": options,
            "recommendation": {
                "most_economical": cheapest["option"],
                "fastest": fastest["option"],
                "value_ratio": f"{cargo_value_usd / cheapest['freight_cost']:.1f}x" if cheapest['freight_cost'] > 0 else "N/A"
            }
        }
    
    return {
        "status": "no_options",
        "message": "No shipping options available for this route"
    }
