"""
🚢 International Logistics Quote Agent - Multi-Agent System
Capstone Project - 5-Day AI Agents Intensive Course with Google

Author: Orihara
Track: Enterprise Agents

Features:
- Multi-Agent System (1 Orchestrator + 3 Specialist Sub-Agents)
- Agent Transfer (Automatic delegation to specialists)
- Custom Tools (11 specialized tools)
- Sessions & Memory (ADK SessionService + Customer memory)
- Observability (Logging and tracing)
- Gemini 2.0 Flash (Optimized for agentic AI)
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# =============================================================================
# LOGGING CONFIGURATION (Observability - Day 4A)
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("logistics_agent")

# =============================================================================
# DUMMY DATA
# =============================================================================

ROUTES_DATA = {
    "sea_routes": [
        {
            "id": "SEA001",
            "origin": {"port": "Tokyo", "port_code": "JPTYO", "country": "Japan"},
            "destination": {"port": "Shanghai", "port_code": "CNSHA", "country": "China"},
            "transit_time_days": 3, "frequency": "Daily",
            "carriers": ["COSCO", "ONE", "Evergreen"], "route_type": "Direct"
        },
        {
            "id": "SEA002",
            "origin": {"port": "Tokyo", "port_code": "JPTYO", "country": "Japan"},
            "destination": {"port": "Suzhou", "port_code": "CNSZH", "country": "China"},
            "transit_time_days": 5, "frequency": "3 times/week",
            "carriers": ["COSCO", "Yang Ming"], "via": "Shanghai", "route_type": "Transshipment"
        },
        {
            "id": "SEA003",
            "origin": {"port": "Yokohama", "port_code": "JPYOK", "country": "Japan"},
            "destination": {"port": "Bangkok", "port_code": "THBKK", "country": "Thailand"},
            "transit_time_days": 12, "frequency": "Weekly",
            "carriers": ["ONE", "Hapag-Lloyd", "MSC"], "via": "Singapore", "route_type": "Transshipment"
        },
        {
            "id": "SEA004",
            "origin": {"port": "Osaka", "port_code": "JPOSA", "country": "Japan"},
            "destination": {"port": "Los Angeles", "port_code": "USLAX", "country": "USA"},
            "transit_time_days": 14, "frequency": "Weekly",
            "carriers": ["ONE", "Matson", "Evergreen"], "route_type": "Direct"
        },
        {
            "id": "SEA005",
            "origin": {"port": "Tokyo", "port_code": "JPTYO", "country": "Japan"},
            "destination": {"port": "Rotterdam", "port_code": "NLRTM", "country": "Netherlands"},
            "transit_time_days": 35, "frequency": "Weekly",
            "carriers": ["Maersk", "MSC"], "via": "Singapore, Suez Canal", "route_type": "Transshipment"
        }
    ],
    "air_routes": [
        {
            "id": "AIR001",
            "origin": {"airport": "Narita", "airport_code": "NRT", "country": "Japan"},
            "destination": {"airport": "Shanghai Pudong", "airport_code": "PVG", "country": "China"},
            "transit_time_days": 1, "frequency": "Daily",
            "carriers": ["ANA Cargo", "JAL Cargo", "China Eastern"], "route_type": "Direct"
        },
        {
            "id": "AIR002",
            "origin": {"airport": "Narita", "airport_code": "NRT", "country": "Japan"},
            "destination": {"airport": "Bangkok Suvarnabhumi", "airport_code": "BKK", "country": "Thailand"},
            "transit_time_days": 1, "frequency": "Daily",
            "carriers": ["Thai Airways", "ANA Cargo"], "route_type": "Direct"
        },
        {
            "id": "AIR003",
            "origin": {"airport": "Kansai", "airport_code": "KIX", "country": "Japan"},
            "destination": {"airport": "Los Angeles", "airport_code": "LAX", "country": "USA"},
            "transit_time_days": 2, "frequency": "Daily",
            "carriers": ["ANA Cargo", "FedEx"], "route_type": "Direct"
        }
    ]
}

RATES_DATA = {
    "sea_freight": {
        "Japan-China": {"20ft": 150, "40ft": 280, "LCL": 45},
        "Japan-Thailand": {"20ft": 350, "40ft": 650, "LCL": 85},
        "Japan-USA": {"20ft": 2500, "40ft": 4500, "LCL": 120},
        "Japan-Europe": {"20ft": 1800, "40ft": 3200, "LCL": 95}
    },
    "air_freight": {
        "Japan-China": {"min": 80, "<45kg": 8.5, "45-100kg": 6.5, "100-300kg": 5.0, "300-500kg": 4.2, ">500kg": 3.5},
        "Japan-Thailand": {"min": 100, "<45kg": 12.0, "45-100kg": 9.0, "100-300kg": 7.5, "300-500kg": 6.0, ">500kg": 5.0},
        "Japan-USA": {"min": 150, "<45kg": 15.0, "45-100kg": 12.0, "100-300kg": 9.5, "300-500kg": 8.0, ">500kg": 6.5}
    },
    "surcharges": {
        "BAF_percent": 15, "CAF_percent": 5,
        "THC_origin": 150, "THC_dest": 180, "doc_fee": 50, "seal_fee": 15,
        "fuel_percent": 25, "security_per_kg": 0.15, "AWB_fee": 30
    },
    "customs": {
        "China": {"doc": 65, "inspect": 100, "handling": 55, "vat": 13},
        "Thailand": {"doc": 55, "inspect": 90, "handling": 50, "vat": 7},
        "USA": {"doc": 100, "inspect": 150, "handling": 75, "vat": 0}
    },
    "duty_rates": {"8471": 0.03, "8479": 0.05, "8501": 0.08, "8517": 0.02},
    "insurance_rate": 0.0035
}

REGULATIONS_DATA = {
    "China": {
        "restricted": ["Used machinery (inspection required)", "Food (CIQ)", "Chemicals (MSDS)"],
        "prohibited": ["Weapons", "Drugs", "Counterfeit goods"],
        "documents": ["Commercial Invoice", "Packing List", "B/L or AWB", "Certificate of Origin"],
        "zones": ["Shanghai FTZ", "Suzhou Industrial Park"]
    },
    "Thailand": {
        "restricted": ["Pharmaceuticals", "Cosmetics", "Medical devices"],
        "prohibited": ["Narcotics", "Pornography", "E-cigarettes"],
        "documents": ["Commercial Invoice", "Packing List", "B/L or AWB", "C/O", "Form D (ASEAN)"],
        "zones": ["Eastern Economic Corridor (EEC)"]
    },
    "USA": {
        "restricted": ["Food (FDA)", "Electronics (FCC)", "Toys (CPSC)"],
        "prohibited": ["Certain agricultural products", "Counterfeit goods"],
        "documents": ["Commercial Invoice", "Packing List", "B/L or AWB", "ISF (10+2)"],
        "zones": []
    }
}

HS_CODES = {
    "8471": {"desc": "Computers and equipment", "duty": "0-5%"},
    "8479": {"desc": "Machines with individual functions", "duty": "0-8%"},
    "8501": {"desc": "Electric motors and generators", "duty": "0-10%"},
    "8517": {"desc": "Communication equipment", "duty": "0-5%"}
}

# =============================================================================
# ROUTE PLANNER TOOLS (3 tools)
# =============================================================================

def search_sea_routes(origin_country: str, destination_country: str) -> dict:
    """
    Search for available sea freight routes between countries.
    
    Args:
        origin_country: Origin country (e.g., "Japan")
        destination_country: Destination country (e.g., "China")
    
    Returns:
        dict: Available sea routes with carriers and transit times
    """
    logger.info(f"🔍 Searching sea routes: {origin_country} → {destination_country}")
    
    routes = []
    for route in ROUTES_DATA["sea_routes"]:
        if (route["origin"]["country"].lower() == origin_country.lower() and
            route["destination"]["country"].lower() == destination_country.lower()):
            routes.append({
                "route_id": route["id"],
                "origin": f"{route['origin']['port']} ({route['origin']['port_code']})",
                "destination": f"{route['destination']['port']} ({route['destination']['port_code']})",
                "transit_days": route["transit_time_days"],
                "frequency": route["frequency"],
                "carriers": route["carriers"],
                "type": route["route_type"],
                "via": route.get("via", "Direct")
            })
    
    if routes:
        return {"status": "success", "mode": "Sea Freight", "count": len(routes), "routes": routes}
    return {"status": "not_found", "message": f"No sea routes from {origin_country} to {destination_country}"}


def search_air_routes(origin_country: str, destination_country: str) -> dict:
    """
    Search for available air freight routes between countries.
    
    Args:
        origin_country: Origin country (e.g., "Japan")
        destination_country: Destination country (e.g., "Thailand")
    
    Returns:
        dict: Available air routes with carriers and transit times
    """
    logger.info(f"✈️ Searching air routes: {origin_country} → {destination_country}")
    
    routes = []
    for route in ROUTES_DATA["air_routes"]:
        if (route["origin"]["country"].lower() == origin_country.lower() and
            route["destination"]["country"].lower() == destination_country.lower()):
            routes.append({
                "route_id": route["id"],
                "origin": f"{route['origin']['airport']} ({route['origin']['airport_code']})",
                "destination": f"{route['destination']['airport']} ({route['destination']['airport_code']})",
                "transit_days": route["transit_time_days"],
                "frequency": route["frequency"],
                "carriers": route["carriers"]
            })
    
    if routes:
        return {"status": "success", "mode": "Air Freight", "count": len(routes), "routes": routes}
    return {"status": "not_found", "message": f"No air routes from {origin_country} to {destination_country}"}


def recommend_transport_mode(
    origin_country: str,
    destination_country: str,
    weight_kg: float,
    volume_cbm: float,
    urgency: str = "normal"
) -> dict:
    """
    Recommend the best transport mode based on cargo and urgency.
    
    Args:
        origin_country: Origin country
        destination_country: Destination country
        weight_kg: Cargo weight in kg
        volume_cbm: Cargo volume in CBM
        urgency: "urgent", "normal", or "economy"
    
    Returns:
        dict: Recommended transport mode with reasoning
    """
    logger.info(f"🎯 Recommending mode: {weight_kg}kg, {volume_cbm}CBM, urgency={urgency}")
    
    recommendations = []
    
    if urgency == "urgent" or (weight_kg <= 300 and volume_cbm <= 1):
        recommendations.append({
            "mode": "Air Freight",
            "priority": 1 if urgency == "urgent" else 2,
            "reason": "Fastest delivery" if urgency == "urgent" else "Cost-effective for small cargo",
            "transit": "1-3 days"
        })
    
    container = "FCL (20ft)" if volume_cbm <= 25 else "FCL (40ft)" if volume_cbm <= 55 else "LCL"
    if volume_cbm < 15:
        container = "LCL"
    
    recommendations.append({
        "mode": f"Sea Freight ({container})",
        "priority": 1 if urgency == "economy" else 2,
        "reason": "Most economical option" if weight_kg > 300 else "Good balance of cost and time",
        "transit": "5-35 days depending on destination"
    })
    
    recommendations.sort(key=lambda x: x["priority"])
    
    return {
        "status": "success",
        "cargo": {"weight_kg": weight_kg, "volume_cbm": volume_cbm, "urgency": urgency},
        "recommendations": recommendations,
        "top_recommendation": recommendations[0]["mode"]
    }

# =============================================================================
# COST ANALYST TOOLS (4 tools)
# =============================================================================

def calculate_sea_freight_cost(
    origin_country: str,
    destination_country: str,
    weight_kg: float,
    volume_cbm: float,
    container_type: str = "LCL"
) -> dict:
    """
    Calculate sea freight cost with full breakdown.
    """
    logger.info(f"💰 Calculating sea freight: {origin_country}→{destination_country}, {container_type}")
    
    lane = f"{origin_country}-{destination_country}"
    rates = RATES_DATA["sea_freight"].get(lane)
    
    if not rates:
        return {"status": "error", "message": f"No rates for {lane}"}
    
    surcharges = RATES_DATA["surcharges"]
    
    if container_type == "LCL":
        chargeable = max(volume_cbm, weight_kg / 1000)
        base = chargeable * rates["LCL"]
    else:
        base = rates.get(container_type, rates["20ft"])
    
    baf = base * surcharges["BAF_percent"] / 100
    caf = base * surcharges["CAF_percent"] / 100
    thc = surcharges["THC_origin"] + surcharges["THC_dest"]
    doc = surcharges["doc_fee"]
    seal = surcharges["seal_fee"] if container_type != "LCL" else 0
    
    total = base + baf + caf + thc + doc + seal
    
    return {
        "status": "success",
        "mode": "Sea Freight",
        "container": container_type,
        "route": lane,
        "breakdown": {
            "base_freight": round(base, 2),
            "BAF": round(baf, 2),
            "CAF": round(caf, 2),
            "THC": thc,
            "documentation": doc,
            "seal": seal
        },
        "total_usd": round(total, 2),
        "validity": "30 days"
    }


def calculate_air_freight_cost(
    origin_country: str,
    destination_country: str,
    weight_kg: float,
    volume_cbm: float
) -> dict:
    """
    Calculate air freight cost with full breakdown.
    """
    logger.info(f"✈️ Calculating air freight: {origin_country}→{destination_country}")
    
    lane = f"{origin_country}-{destination_country}"
    rates = RATES_DATA["air_freight"].get(lane)
    
    if not rates:
        return {"status": "error", "message": f"No air rates for {lane}"}
    
    surcharges = RATES_DATA["surcharges"]
    
    vol_weight = volume_cbm * 1000000 / 6000
    chargeable = max(weight_kg, vol_weight)
    
    if chargeable < 45:
        rate = rates["<45kg"]
    elif chargeable < 100:
        rate = rates["45-100kg"]
    elif chargeable < 300:
        rate = rates["100-300kg"]
    elif chargeable < 500:
        rate = rates["300-500kg"]
    else:
        rate = rates[">500kg"]
    
    base = max(chargeable * rate, rates["min"])
    fuel = base * surcharges["fuel_percent"] / 100
    security = chargeable * surcharges["security_per_kg"]
    awb = surcharges["AWB_fee"]
    
    total = base + fuel + security + awb
    
    return {
        "status": "success",
        "mode": "Air Freight",
        "route": lane,
        "weight": {
            "actual_kg": weight_kg,
            "volumetric_kg": round(vol_weight, 2),
            "chargeable_kg": round(chargeable, 2),
            "rate_per_kg": rate
        },
        "breakdown": {
            "base_freight": round(base, 2),
            "fuel_surcharge": round(fuel, 2),
            "security": round(security, 2),
            "AWB_fee": awb
        },
        "total_usd": round(total, 2),
        "validity": "7 days"
    }


def calculate_total_landed_cost(
    freight_cost: float,
    cargo_value: float,
    destination_country: str,
    hs_code: str = "8479"
) -> dict:
    """
    Calculate total landed cost including duties, taxes, and customs fees.
    """
    logger.info(f"📊 Calculating landed cost: ${cargo_value} to {destination_country}")
    
    customs = RATES_DATA["customs"].get(destination_country, RATES_DATA["customs"]["China"])
    duty_rate = RATES_DATA["duty_rates"].get(hs_code[:4], 0.05)
    insurance_rate = RATES_DATA["insurance_rate"]
    
    insurance = max(cargo_value * 1.1 * insurance_rate, 25)
    cif = cargo_value + freight_cost + insurance
    duty = cargo_value * duty_rate
    vat = (cargo_value + duty) * customs["vat"] / 100
    customs_total = customs["doc"] + customs["inspect"] + customs["handling"]
    total = cif + duty + vat + customs_total
    
    return {
        "status": "success",
        "destination": destination_country,
        "hs_code": hs_code,
        "value_breakdown": {
            "cargo_FOB": cargo_value,
            "freight": freight_cost,
            "insurance": round(insurance, 2),
            "CIF_value": round(cif, 2)
        },
        "duties_taxes": {
            "duty": round(duty, 2),
            "duty_rate": f"{duty_rate*100}%",
            "VAT": round(vat, 2),
            "VAT_rate": f"{customs['vat']}%"
        },
        "customs_fees": customs_total,
        "total_landed_cost_usd": round(total, 2)
    }


def compare_shipping_options(
    origin_country: str,
    destination_country: str,
    weight_kg: float,
    volume_cbm: float,
    cargo_value: float
) -> dict:
    """
    Compare all shipping options side by side.
    """
    logger.info(f"⚖️ Comparing options: {origin_country}→{destination_country}")
    
    options = []
    
    sea = calculate_sea_freight_cost(origin_country, destination_country, weight_kg, volume_cbm, "LCL")
    if sea["status"] == "success":
        options.append({
            "option": "Sea Freight (LCL)",
            "freight_cost": sea["total_usd"],
            "transit": "5-14 days",
            "best_for": "Cost-sensitive, non-urgent"
        })
    
    air = calculate_air_freight_cost(origin_country, destination_country, weight_kg, volume_cbm)
    if air["status"] == "success":
        options.append({
            "option": "Air Freight",
            "freight_cost": air["total_usd"],
            "transit": "1-3 days",
            "best_for": "Urgent, high-value goods"
        })
    
    options.sort(key=lambda x: x["freight_cost"])
    
    return {
        "status": "success",
        "cargo": {"weight_kg": weight_kg, "volume_cbm": volume_cbm, "value_usd": cargo_value},
        "options": options,
        "recommendation": {
            "cheapest": options[0]["option"] if options else "N/A",
            "savings": round(options[-1]["freight_cost"] - options[0]["freight_cost"], 2) if len(options) > 1 else 0
        }
    }

# =============================================================================
# DOCUMENT SPECIALIST TOOLS (4 tools)
# =============================================================================

def get_required_documents(
    origin_country: str,
    destination_country: str,
    transport_mode: str = "sea"
) -> dict:
    """
    Get list of required shipping documents.
    """
    logger.info(f"📄 Getting documents: {origin_country}→{destination_country} ({transport_mode})")
    
    docs = [
        {"name": "Commercial Invoice", "copies": 3, "purpose": "Value declaration for customs"},
        {"name": "Packing List", "copies": 3, "purpose": "Contents and weights of packages"},
    ]
    
    if transport_mode.lower() == "sea":
        docs.append({"name": "Bill of Lading (B/L)", "copies": "3 originals", "purpose": "Title document"})
    else:
        docs.append({"name": "Air Waybill (AWB)", "copies": "Original", "purpose": "Contract of carriage"})
    
    docs.append({"name": "Certificate of Origin", "copies": 1, "purpose": "For preferential duty rates (RCEP)"})
    
    additional = []
    if destination_country == "USA":
        additional.append({"name": "ISF (10+2)", "deadline": "24h before departure"})
    if destination_country == "Thailand":
        additional.append({"name": "Form D", "purpose": "ASEAN preferential tariff"})
    
    return {
        "status": "success",
        "route": f"{origin_country} → {destination_country}",
        "transport": transport_mode,
        "required_documents": docs,
        "additional": additional
    }


def check_customs_regulations(destination_country: str, product_type: str = "machinery") -> dict:
    """
    Check customs regulations for importing goods.
    """
    logger.info(f"🛃 Checking regulations: {destination_country} for {product_type}")
    
    regs = REGULATIONS_DATA.get(destination_country)
    if not regs:
        return {"status": "limited", "message": f"Limited info for {destination_country}"}
    
    customs = RATES_DATA["customs"].get(destination_country, {})
    
    return {
        "status": "success",
        "country": destination_country,
        "vat_rate": f"{customs.get('vat', 'N/A')}%",
        "restricted_items": regs["restricted"],
        "prohibited_items": regs["prohibited"],
        "required_documents": regs["documents"],
        "special_zones": regs["zones"]
    }


def get_hs_code_info(hs_code: str) -> dict:
    """
    Get HS code information and typical duty rates.
    """
    logger.info(f"🔢 Looking up HS code: {hs_code}")
    
    info = HS_CODES.get(hs_code[:4])
    if info:
        return {
            "status": "success",
            "hs_code": hs_code,
            "description": info["desc"],
            "typical_duty": info["duty"]
        }
    return {"status": "not_found", "hs_code": hs_code}


def generate_shipping_checklist(
    origin_country: str,
    destination_country: str,
    transport_mode: str = "sea"
) -> dict:
    """
    Generate complete shipping preparation checklist.
    """
    logger.info(f"📋 Generating checklist: {origin_country}→{destination_country}")
    
    today = datetime.now()
    transit = 3 if transport_mode == "air" else 10
    
    timeline = [
        {"day": 0, "task": "Booking confirmation", "date": today.strftime("%Y-%m-%d")},
        {"day": 2, "task": "Cargo ready", "date": (today + timedelta(days=2)).strftime("%Y-%m-%d")},
        {"day": 3, "task": "Departure", "date": (today + timedelta(days=3)).strftime("%Y-%m-%d")},
        {"day": 3+transit, "task": "Arrival", "date": (today + timedelta(days=3+transit)).strftime("%Y-%m-%d")},
        {"day": 5+transit, "task": "Delivery", "date": (today + timedelta(days=5+transit)).strftime("%Y-%m-%d")},
    ]
    
    return {
        "status": "success",
        "route": f"{origin_country} → {destination_country}",
        "timeline": timeline
    }

# =============================================================================
# MEMORY TOOLS (Shared)
# =============================================================================

customer_memory = {}
quote_history = []


def save_customer_info(customer_id: str, info_type: str, value: str) -> dict:
    """Save customer information for personalized service."""
    logger.info(f"💾 Saving customer info: {customer_id} - {info_type}")
    
    if customer_id not in customer_memory:
        customer_memory[customer_id] = {}
    customer_memory[customer_id][info_type] = {"value": value, "saved_at": datetime.now().isoformat()}
    
    return {"status": "success", "message": f"Saved {info_type} for {customer_id}"}


def get_customer_info(customer_id: str) -> dict:
    """Retrieve stored customer information."""
    if customer_id not in customer_memory:
        return {"status": "not_found", "message": f"No info for {customer_id}"}
    info = {k: v["value"] for k, v in customer_memory[customer_id].items()}
    return {"status": "success", "customer_id": customer_id, "info": info}


def save_quote(
    customer_id: str,
    origin: str,
    destination: str,
    cargo_desc: str,
    total_cost: float,
    transport_mode: str
) -> dict:
    """
    Save a shipping quote for future reference. Use this when user asks to save, store, or keep the quote.
    
    Args:
        customer_id: Customer identifier (use session user ID)
        origin: Origin location (e.g., "Tokyo, Japan")
        destination: Destination location (e.g., "Shanghai, China")
        cargo_desc: Description of cargo (e.g., "500kg machinery 2.42CBM")
        total_cost: Total cost in USD (e.g., 510.68)
        transport_mode: Transport mode ("Sea" or "Air")
    
    Returns:
        dict: Quote ID and validity period
    """
    quote_id = f"Q{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    quote = {
        "quote_id": quote_id,
        "customer_id": customer_id,
        "created": datetime.now().isoformat(),
        "origin": origin,
        "destination": destination,
        "cargo": cargo_desc,
        "cost_usd": total_cost,
        "mode": transport_mode,
        "valid_until": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    }
    
    quote_history.append(quote)
    logger.info(f"📝 Quote saved: {quote_id}")
    
    return {"status": "success", "quote_id": quote_id, "valid_until": quote["valid_until"]}


def get_quote_history(customer_id: str = None) -> dict:
    """Retrieve quote history."""
    if customer_id:
        quotes = [q for q in quote_history if q["customer_id"] == customer_id]
    else:
        quotes = quote_history
    return {"status": "success", "count": len(quotes), "quotes": quotes[-10:]}

# =============================================================================
# SUB-AGENT DEFINITIONS
# =============================================================================

route_planner_agent = Agent(
    model="gemini-2.0-flash",
    name="route_planner",
    description="Specialist in finding optimal shipping routes. Call for route searches and transport recommendations.",
    instruction="""You are a Route Planning Specialist for international logistics.

Your expertise:
- Finding sea and air freight routes
- Recommending the best transport mode based on cargo characteristics

When asked about routes:
1. Use search_sea_routes and/or search_air_routes
2. Use recommend_transport_mode to suggest the best option
3. Present routes clearly with transit times and carriers
""",
    tools=[search_sea_routes, search_air_routes, recommend_transport_mode]
)

cost_analyst_agent = Agent(
    model="gemini-2.0-flash",
    name="cost_analyst",
    description="Specialist in calculating shipping costs. Call for pricing and cost comparisons.",
    instruction="""You are a Cost Analysis Specialist for international logistics.

Your expertise:
- Calculating sea and air freight costs
- Computing total landed costs including duties
- Comparing different shipping options

When asked about costs:
1. Use calculate_sea_freight_cost or calculate_air_freight_cost
2. Use calculate_total_landed_cost for complete cost
3. Use compare_shipping_options to show all options
""",
    tools=[calculate_sea_freight_cost, calculate_air_freight_cost, calculate_total_landed_cost, compare_shipping_options]
)

document_specialist_agent = Agent(
    model="gemini-2.0-flash",
    name="document_specialist",
    description="Specialist in shipping documentation and customs. Call for document requirements and regulations.",
    instruction="""You are a Documentation and Customs Specialist.

Your expertise:
- Required shipping documents
- Customs regulations and restrictions
- HS code classification

When asked about documents or customs:
1. Use get_required_documents for document lists
2. Use check_customs_regulations for import rules
3. Use get_hs_code_info for tariff classification
4. Use generate_shipping_checklist for preparation guides
""",
    tools=[get_required_documents, check_customs_regulations, get_hs_code_info, generate_shipping_checklist]
)

# NEW: Quote Manager Agent for saving and retrieving quotes
quote_manager_agent = Agent(
    model="gemini-2.0-flash",
    name="quote_manager",
    description="Specialist in saving and managing quotes. Call this agent when user wants to save a quote, store a quote, retrieve quotes, or manage customer information. Keywords: save, store, keep, 保存, 記録, history, 履歴",
    instruction="""You are a Quote Management Specialist.

Your job is to save quotes and manage customer information.

YOUR TOOLS:
1. **save_quote** - Save a shipping quote
2. **get_quote_history** - Get past quotes  
3. **save_customer_info** - Save customer preferences
4. **get_customer_info** - Get customer info

WHEN TO ACT:
When user says:
- "save this quote" / "save quote" / "store quote"
- "保存して" / "見積もりを保存" / "この見積もりを保存して"
- "keep this quote" / "記録して"

HOW TO SAVE A QUOTE:
Call save_quote with:
- customer_id: Get from conversation context (e.g., "001")
- origin: Origin city/country (e.g., "Tokyo, Japan")
- destination: Destination city/country (e.g., "Shanghai, China")
- cargo_desc: Cargo info (e.g., "500kg 2CBM machinery")
- total_cost: The price number (e.g., 488.0)
- transport_mode: "Sea" or "Air"

ALWAYS save when asked. Never say you cannot save.
""",
    tools=[save_quote, get_quote_history, save_customer_info, get_customer_info]
)

# =============================================================================
# ORCHESTRATOR AGENT
# =============================================================================

logistics_coordinator = Agent(
    model="gemini-2.0-flash",
    name="logistics_coordinator",
    description="International Logistics Quote Agent - Coordinates specialist agents for comprehensive shipping solutions.",
    instruction="""You are the Logistics Coordinator, leading a team of specialist agents.

YOUR TEAM:
1. **route_planner** - Expert in finding shipping routes
2. **cost_analyst** - Expert in calculating costs and quotes
3. **document_specialist** - Expert in documents and customs
4. **quote_manager** - Expert in saving and retrieving quotes

DELEGATION RULES:
- Route questions → route_planner
- Cost/pricing questions → cost_analyst
- Document/customs questions → document_specialist
- Save quote / 保存 / store / keep → quote_manager
- Quote history / 履歴 → quote_manager
- Customer info → quote_manager

IMPORTANT: When user asks to save a quote (保存して, save this quote, etc.),
ALWAYS delegate to quote_manager agent.

Always be professional and provide complete information.
Respond in the same language as the user.
""",
    tools=[],  # No direct tools, all delegated to sub-agents
    sub_agents=[route_planner_agent, cost_analyst_agent, document_specialist_agent, quote_manager_agent]
)

# Debug: Show registered agents
print(f"✅ Coordinator with 4 sub-agents: route_planner, cost_analyst, document_specialist, quote_manager")

# =============================================================================
# DEMO FUNCTION
# =============================================================================

async def run_demo():
    """Run demonstration of the multi-agent logistics system."""
    
    print("=" * 70)
    print("🚢 International Logistics Quote Agent - Multi-Agent Demo")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not set in .env file")
        return
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="logistics_multi_agent",
        user_id="demo_customer"
    )
    
    runner = Runner(
        agent=logistics_coordinator,
        app_name="logistics_multi_agent",
        session_service=session_service
    )
    
    demo_queries = [
        "What shipping routes are available from Japan to China?",
        "Compare sea and air freight costs for 500kg machinery (2 CBM, $15,000) from Japan to China.",
        "What documents do I need for shipping to China by sea?",
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*60}")
        print(f"📝 Query {i}: {query}")
        print(f"{'='*60}")
        
        content = types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="demo_customer",
            session_id=session.id,
            new_message=content
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text
        
        print(f"\n🤖 Response:\n{response_text}")
    
    print(f"\n{'='*70}")
    print("✅ Multi-Agent Demo completed!")
    print(f"{'='*70}")


async def interactive_mode():
    """Run in interactive mode."""
    
    print("=" * 70)
    print("🚢 International Logistics Quote Agent - Interactive Mode")
    print("=" * 70)
    print("Type 'quit' to exit")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not set")
        return
    
    session_service = InMemorySessionService()
    
    customer_id = input("\n👤 Enter customer ID (or press Enter for 'guest'): ").strip() or "guest"
    
    session = await session_service.create_session(
        app_name="logistics_multi_agent",
        user_id=customer_id
    )
    
    runner = Runner(
        agent=logistics_coordinator,
        app_name="logistics_multi_agent",
        session_service=session_service
    )
    
    print(f"\n✅ Session started for: {customer_id}")
    print("\nHow can I help you with your shipping needs today?\n")
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() == 'quit':
                print("\n👋 Thank you for using our service!")
                break
            
            if not user_input:
                continue
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
            
            response_text = ""
            async for event in runner.run_async(
                user_id=customer_id,
                session_id=session.id,
                new_message=content
            ):
                if event.is_final_response():
                    response_text = event.content.parts[0].text
            
            print(f"\n🤖 Agent: {response_text}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Session ended.")
            break

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(run_demo())