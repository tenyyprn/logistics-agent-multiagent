"""
Document Tools for Logistics Agent
書類関連ツール
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_regulations_data() -> dict:
    """規制データを読み込む"""
    reg_file = os.path.join(DATA_DIR, "regulations.json")
    if os.path.exists(reg_file):
        with open(reg_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_required_documents(
    origin_country: str,
    destination_country: str,
    transport_mode: str = "sea"
) -> dict:
    """
    Get list of required shipping documents for the route.
    ルートに必要な船積書類のリストを取得します。

    Args:
        origin_country: Origin country
        destination_country: Destination country
        transport_mode: "sea" or "air"

    Returns:
        dict: List of required documents with descriptions
    """
    data = load_regulations_data()
    countries = data.get("countries", {})
    
    dest_info = countries.get(destination_country, {})
    origin_info = countries.get(origin_country, {})
    
    # Base documents
    base_docs = [
        {
            "document": "Commercial Invoice",
            "required": True,
            "description": "Detailed invoice showing seller, buyer, goods description, quantity, unit price, and total value",
            "copies_needed": 3
        },
        {
            "document": "Packing List",
            "required": True,
            "description": "Detailed list of all items, dimensions, weights, and package numbers",
            "copies_needed": 3
        }
    ]
    
    # Transport document
    if transport_mode.lower() == "sea":
        base_docs.append({
            "document": "Bill of Lading (B/L)",
            "required": True,
            "description": "Contract of carriage and receipt of goods by the shipping line",
            "copies_needed": "3 originals + copies"
        })
    else:
        base_docs.append({
            "document": "Air Waybill (AWB)",
            "required": True,
            "description": "Contract of carriage and receipt of goods by the airline",
            "copies_needed": "Original + copies"
        })
    
    # Certificate of Origin
    trade_agreements = data.get("trade_agreements", {})
    co_info = {
        "document": "Certificate of Origin",
        "required": True,
        "description": "Document certifying the country where goods were manufactured",
        "copies_needed": 1
    }
    
    # Check for preferential origin certificates
    if destination_country in ["China", "Thailand", "South Korea"]:
        co_info["preferential_option"] = "RCEP Certificate of Origin for reduced duties"
    if destination_country == "Thailand" and origin_country == "Japan":
        co_info["preferential_option"] = "Form JTEPA for Japan-Thailand EPA benefits"
    
    base_docs.append(co_info)
    
    # Destination-specific documents
    dest_regs = dest_info.get("import_regulations", {})
    additional_docs = []
    
    if destination_country == "USA":
        additional_docs.append({
            "document": "ISF (Importer Security Filing)",
            "required": True,
            "description": "10+2 filing required 24 hours before vessel departure",
            "deadline": "24 hours before vessel departure"
        })
    
    if destination_country == "China":
        additional_docs.append({
            "document": "China Inspection Certificate (if applicable)",
            "required": "For certain goods",
            "description": "CIQ inspection certificate for food, cosmetics, and certain machinery"
        })
    
    # Export documents from origin
    origin_regs = origin_info.get("export_regulations", {})
    if origin_country == "Japan":
        additional_docs.append({
            "document": "Shipper's Export Declaration",
            "required": True,
            "description": "Export declaration submitted via NACCS system"
        })
    
    return {
        "status": "success",
        "route": f"{origin_country} → {destination_country}",
        "transport_mode": transport_mode.capitalize(),
        "required_documents": base_docs,
        "additional_documents": additional_docs,
        "notes": [
            "Document requirements may vary based on specific goods",
            "Always verify current requirements with customs broker",
            "Some goods may require additional licenses or permits"
        ]
    }


def check_customs_regulations(
    destination_country: str,
    product_category: str
) -> dict:
    """
    Check customs regulations and requirements for importing goods.
    輸入貨物の通関規制と要件を確認します。

    Args:
        destination_country: Destination country
        product_category: Type of product (e.g., "machinery", "electronics", "food")

    Returns:
        dict: Customs regulations and requirements
    """
    data = load_regulations_data()
    countries = data.get("countries", {})
    
    country_info = countries.get(destination_country, {})
    import_regs = country_info.get("import_regulations", {})
    
    if not import_regs:
        return {
            "status": "info_limited",
            "message": f"Detailed regulations for {destination_country} not in database",
            "recommendation": "Please consult with a licensed customs broker"
        }
    
    # Get duty rate for category
    duties = import_regs.get("customs_duties", {})
    duty_rate = duties.get(product_category.lower(), "Rate varies - consult tariff schedule")
    
    return {
        "status": "success",
        "country": destination_country,
        "product_category": product_category,
        "duty_information": {
            "estimated_duty_rate": duty_rate,
            "vat_rate": f"{import_regs.get('vat_rate', 'N/A')}%"
        },
        "restricted_items": import_regs.get("restricted_items", []),
        "prohibited_items": import_regs.get("prohibited_items", []),
        "required_documents": import_regs.get("required_documents", []),
        "special_economic_zones": import_regs.get("special_zones", []),
        "important_notes": [
            "Rates are estimates and subject to change",
            "Classification depends on actual HS code determination",
            "Some products may require import licenses"
        ]
    }


def get_hs_code_info(hs_code: str) -> dict:
    """
    Get information about an HS code including typical duty rates.
    HSコードに関する情報（一般的な関税率を含む）を取得します。

    Args:
        hs_code: Harmonized System code (4-6 digits)

    Returns:
        dict: HS code information and typical duty rates
    """
    data = load_regulations_data()
    hs_codes = data.get("hs_codes_common", {})
    
    # Try exact match first, then prefix match
    code_info = hs_codes.get(hs_code)
    if not code_info:
        for code, info in hs_codes.items():
            if hs_code.startswith(code) or code.startswith(hs_code[:4]):
                code_info = info
                break
    
    if code_info:
        return {
            "status": "success",
            "hs_code": hs_code,
            "description": code_info.get("description", "Description not available"),
            "typical_duty_range": code_info.get("typical_duty_range", "Varies by country"),
            "notes": [
                "Actual HS code classification should be verified by customs authority",
                "Duty rates vary by destination country and trade agreements",
                "Incorrect classification may result in penalties"
            ]
        }
    
    return {
        "status": "not_found",
        "hs_code": hs_code,
        "message": "HS code not found in database",
        "recommendation": "Consult the official HS tariff schedule or a customs broker for accurate classification"
    }


def generate_shipping_checklist(
    origin_country: str,
    destination_country: str,
    transport_mode: str,
    incoterm: str = "FOB"
) -> dict:
    """
    Generate a comprehensive shipping checklist.
    包括的な出荷チェックリストを生成します。

    Args:
        origin_country: Origin country
        destination_country: Destination country
        transport_mode: "sea" or "air"
        incoterm: Incoterm (FOB, CIF, EXW, etc.)

    Returns:
        dict: Complete shipping checklist
    """
    docs = get_required_documents(origin_country, destination_country, transport_mode)
    
    checklist = {
        "status": "success",
        "shipment_details": {
            "route": f"{origin_country} → {destination_country}",
            "transport_mode": transport_mode.capitalize(),
            "incoterm": incoterm
        },
        "pre_shipment_checklist": [
            {"task": "Confirm order details with buyer", "responsible": "Shipper"},
            {"task": "Book cargo space with carrier", "responsible": "Shipper/Forwarder"},
            {"task": "Arrange cargo insurance", "responsible": incoterm_responsibility(incoterm, "insurance")},
            {"task": "Prepare commercial invoice", "responsible": "Shipper"},
            {"task": "Prepare packing list", "responsible": "Shipper"},
            {"task": "Obtain certificate of origin", "responsible": "Shipper"},
            {"task": "Check export license requirements", "responsible": "Shipper"},
        ],
        "loading_checklist": [
            {"task": "Inspect packaging condition", "responsible": "Shipper"},
            {"task": "Verify cargo weight and dimensions", "responsible": "Shipper"},
            {"task": "Take photographs of cargo", "responsible": "Shipper"},
            {"task": "Obtain signed delivery receipt", "responsible": "Shipper"},
        ],
        "documentation_checklist": docs.get("required_documents", []),
        "post_shipment_checklist": [
            {"task": "Send documents to consignee/bank", "responsible": "Shipper"},
            {"task": "Track shipment status", "responsible": "Shipper/Forwarder"},
            {"task": "Coordinate with destination customs broker", "responsible": "Consignee"},
            {"task": "Confirm delivery and obtain POD", "responsible": "Consignee"},
        ],
        "timeline_guide": generate_timeline(transport_mode, origin_country, destination_country)
    }
    
    return checklist


def incoterm_responsibility(incoterm: str, item: str) -> str:
    """Determine responsibility based on Incoterm"""
    responsibilities = {
        "EXW": {"insurance": "Buyer", "freight": "Buyer"},
        "FOB": {"insurance": "Buyer", "freight": "Buyer"},
        "CFR": {"insurance": "Buyer", "freight": "Seller"},
        "CIF": {"insurance": "Seller", "freight": "Seller"},
        "DAP": {"insurance": "Seller", "freight": "Seller"},
        "DDP": {"insurance": "Seller", "freight": "Seller"},
    }
    return responsibilities.get(incoterm, {}).get(item, "Check contract")


def generate_timeline(transport_mode: str, origin: str, destination: str) -> list:
    """Generate estimated timeline"""
    today = datetime.now()
    
    if transport_mode.lower() == "air":
        return [
            {"day": 0, "event": "Booking confirmation", "date": today.strftime("%Y-%m-%d")},
            {"day": 1, "event": "Cargo pickup and export customs", "date": (today + timedelta(days=1)).strftime("%Y-%m-%d")},
            {"day": 2, "event": "Flight departure", "date": (today + timedelta(days=2)).strftime("%Y-%m-%d")},
            {"day": 3, "event": "Arrival and import customs", "date": (today + timedelta(days=3)).strftime("%Y-%m-%d")},
            {"day": 4, "event": "Delivery to consignee", "date": (today + timedelta(days=4)).strftime("%Y-%m-%d")},
        ]
    else:
        transit_days = 7 if "China" in destination else 14
        return [
            {"day": 0, "event": "Booking confirmation", "date": today.strftime("%Y-%m-%d")},
            {"day": 3, "event": "Container stuffing and export customs", "date": (today + timedelta(days=3)).strftime("%Y-%m-%d")},
            {"day": 5, "event": "Vessel departure", "date": (today + timedelta(days=5)).strftime("%Y-%m-%d")},
            {"day": 5 + transit_days, "event": "Vessel arrival", "date": (today + timedelta(days=5+transit_days)).strftime("%Y-%m-%d")},
            {"day": 7 + transit_days, "event": "Import customs clearance", "date": (today + timedelta(days=7+transit_days)).strftime("%Y-%m-%d")},
            {"day": 10 + transit_days, "event": "Delivery to consignee", "date": (today + timedelta(days=10+transit_days)).strftime("%Y-%m-%d")},
        ]
