"""
Route Search Tools for Logistics Agent
ルート検索ツール
"""

import json
import os
from typing import Optional

# データファイルのパス
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_routes_data() -> dict:
    """ルートデータを読み込む"""
    routes_file = os.path.join(DATA_DIR, "routes.json")
    if os.path.exists(routes_file):
        with open(routes_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sea_routes": [], "air_routes": [], "truck_routes": []}


def search_sea_routes(
    origin_country: str,
    destination_country: str,
    origin_port: Optional[str] = None,
    destination_port: Optional[str] = None
) -> dict:
    """
    Search for available sea freight routes between countries.
    海上輸送ルートを検索します。

    Args:
        origin_country: Origin country name (e.g., "Japan")
        destination_country: Destination country name (e.g., "China")
        origin_port: Optional specific origin port (e.g., "Tokyo")
        destination_port: Optional specific destination port (e.g., "Shanghai")

    Returns:
        dict: Available sea routes with transit times and carriers
    """
    data = load_routes_data()
    routes = []
    
    for route in data.get("sea_routes", []):
        origin_match = route["origin"]["country"].lower() == origin_country.lower()
        dest_match = route["destination"]["country"].lower() == destination_country.lower()
        
        if origin_match and dest_match:
            # Check specific ports if provided
            if origin_port and origin_port.lower() not in route["origin"]["port"].lower():
                continue
            if destination_port and destination_port.lower() not in route["destination"]["port"].lower():
                continue
            
            routes.append({
                "route_id": route["id"],
                "origin": f"{route['origin']['port']} ({route['origin']['port_code']})",
                "destination": f"{route['destination']['port']} ({route['destination']['port_code']})",
                "transit_time_days": route["transit_time_days"],
                "frequency": route["frequency"],
                "carriers": route["carriers"],
                "route_type": route["route_type"],
                "via": route.get("via", "Direct")
            })
    
    if routes:
        return {
            "status": "success",
            "transport_mode": "Sea Freight",
            "route_count": len(routes),
            "routes": routes
        }
    else:
        return {
            "status": "no_routes_found",
            "message": f"No sea routes found from {origin_country} to {destination_country}",
            "suggestion": "Try air freight or check nearby ports"
        }


def search_air_routes(
    origin_country: str,
    destination_country: str,
    origin_airport: Optional[str] = None,
    destination_airport: Optional[str] = None
) -> dict:
    """
    Search for available air freight routes between countries.
    航空輸送ルートを検索します。

    Args:
        origin_country: Origin country name (e.g., "Japan")
        destination_country: Destination country name (e.g., "China")
        origin_airport: Optional specific origin airport (e.g., "Narita")
        destination_airport: Optional specific destination airport

    Returns:
        dict: Available air routes with transit times and carriers
    """
    data = load_routes_data()
    routes = []
    
    for route in data.get("air_routes", []):
        origin_match = route["origin"]["country"].lower() == origin_country.lower()
        dest_match = route["destination"]["country"].lower() == destination_country.lower()
        
        if origin_match and dest_match:
            if origin_airport and origin_airport.lower() not in route["origin"]["airport"].lower():
                continue
            if destination_airport and destination_airport.lower() not in route["destination"]["airport"].lower():
                continue
            
            routes.append({
                "route_id": route["id"],
                "origin": f"{route['origin']['airport']} ({route['origin']['airport_code']})",
                "destination": f"{route['destination']['airport']} ({route['destination']['airport_code']})",
                "transit_time_days": route["transit_time_days"],
                "frequency": route["frequency"],
                "carriers": route["carriers"],
                "route_type": route["route_type"]
            })
    
    if routes:
        return {
            "status": "success",
            "transport_mode": "Air Freight",
            "route_count": len(routes),
            "routes": routes
        }
    else:
        return {
            "status": "no_routes_found",
            "message": f"No air routes found from {origin_country} to {destination_country}",
            "suggestion": "Try sea freight or check nearby airports"
        }


def recommend_transport_mode(
    origin_country: str,
    destination_country: str,
    cargo_weight_kg: float,
    cargo_volume_cbm: float,
    urgency: str = "normal"
) -> dict:
    """
    Recommend the best transport mode based on cargo details and urgency.
    貨物の詳細と緊急度に基づいて最適な輸送モードを推奨します。

    Args:
        origin_country: Origin country
        destination_country: Destination country
        cargo_weight_kg: Total cargo weight in kilograms
        cargo_volume_cbm: Total cargo volume in cubic meters
        urgency: Urgency level - "urgent", "normal", or "economy"

    Returns:
        dict: Recommended transport mode with reasoning
    """
    # Search available routes
    sea_routes = search_sea_routes(origin_country, destination_country)
    air_routes = search_air_routes(origin_country, destination_country)
    
    recommendations = []
    
    # Air freight logic
    if air_routes["status"] == "success":
        air_transit = air_routes["routes"][0]["transit_time_days"]
        
        if urgency == "urgent":
            recommendations.append({
                "mode": "Air Freight",
                "priority": 1,
                "transit_days": air_transit,
                "reason": "Fastest option for urgent shipments",
                "best_for": "Time-sensitive, high-value, or lightweight cargo"
            })
        elif cargo_weight_kg <= 500 and cargo_volume_cbm <= 2:
            recommendations.append({
                "mode": "Air Freight",
                "priority": 2,
                "transit_days": air_transit,
                "reason": "Cost-effective for small shipments",
                "best_for": "Lightweight cargo under 500kg"
            })
    
    # Sea freight logic
    if sea_routes["status"] == "success":
        sea_transit = sea_routes["routes"][0]["transit_time_days"]
        
        if urgency == "economy" or cargo_weight_kg > 500:
            recommendations.append({
                "mode": "Sea Freight (FCL)" if cargo_volume_cbm >= 15 else "Sea Freight (LCL)",
                "priority": 1 if urgency == "economy" else 2,
                "transit_days": sea_transit,
                "reason": "Most economical for large shipments" if cargo_weight_kg > 500 else "Good balance of cost and time",
                "best_for": "Heavy or bulky cargo, cost-sensitive shipments"
            })
        elif cargo_volume_cbm >= 25:
            recommendations.append({
                "mode": "Sea Freight (FCL)",
                "priority": 1,
                "transit_days": sea_transit,
                "reason": "Full container load is most economical for large volumes",
                "container_suggestion": "40ft container" if cargo_volume_cbm > 30 else "20ft container"
            })
    
    # Sort by priority
    recommendations.sort(key=lambda x: x["priority"])
    
    return {
        "status": "success",
        "cargo_summary": {
            "weight_kg": cargo_weight_kg,
            "volume_cbm": cargo_volume_cbm,
            "urgency": urgency
        },
        "recommendations": recommendations,
        "note": "Final selection should consider total cost and specific requirements"
    }
