"""
Starbucks Capacity Dashboard - Backend Server
Queries Epicor REST API directly and serves data to frontend
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
from requests.auth import HTTPBasicAuth
import os
from datetime import datetime
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__, static_folder='.')
CORS(app)

# Epicor REST API Configuration - v1 API
EPICOR_CONFIG = {
    "base_url": "https://centralusdtapp20.epicorsaas.com/SaaS704/api/v1",
    "username": os.environ.get("EPICOR_USERNAME", "Claude.AI"),
    "password": os.environ.get("EPICOR_PASSWORD", "@Mtrend2026"),
    "api_key": os.environ.get("EPICOR_API_KEY", "LgbgeQtNgh5GzbS27ZFpbeFigdJzQ4HEI6QpqBytRF8Xn"),
    "company": "28648"  # Company ID for authentication
}

# Master BOM from Quote 109209
MASTER_BOM = {
    "SBX-22721": {
        "description": "Moon Chair, Fern Green F0244",
        "starbucksPartNum": "11174933",
        "quoteLine": "109209-5",
        "components": {
            "SBX-118": {"qty": 1.0, "uom": "EA", "type": "Frame"},
            "LEA-SBX14": {"qty": 55.0, "uom": "SQFT", "type": "Leather"},
            "FOAM-171": {"qty": 1.0, "uom": "EA", "type": "Pattern"},
            "FOAM-136": {"qty": 0.75, "uom": "EA", "type": "Foam"},
            "FOAM-130": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-125": {"qty": 0.33, "uom": "EA", "type": "Foam"},
            "FOAM-132": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "POLB-129": {"qty": 1.0, "uom": "RL", "type": "Packaging"},
            "CTNS-117": {"qty": 1.0, "uom": "EA", "type": "Packaging"}
        }
    },
    "SBX-24540": {
        "description": "Comf Chair, Fern Green F0244",
        "starbucksPartNum": "11174936",
        "quoteLine": "109209-1",
        "components": {
            "SBX-119": {"qty": 1.0, "uom": "EA", "type": "Frame"},
            "LEA-SBX14": {"qty": 90.0, "uom": "SQFT", "type": "Leather"},
            "FOAM-170": {"qty": 1.0, "uom": "EA", "type": "Pattern"},
            "FOAM-130": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-132": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-125": {"qty": 0.33, "uom": "EA", "type": "Foam"},
            "POLB-129": {"qty": 1.0, "uom": "RL", "type": "Packaging"},
            "CTNS-118": {"qty": 1.0, "uom": "EA", "type": "Packaging"}
        }
    },
    "SBX-24541": {
        "description": "Comf Chair, Roast Natural F0262",
        "starbucksPartNum": "11174939",
        "quoteLine": "109209-2",
        "components": {
            "SBX-119": {"qty": 1.0, "uom": "EA", "type": "Frame"},
            "LEA-SBX16": {"qty": 90.0, "uom": "SQFT", "type": "Leather"},
            "FOAM-170": {"qty": 1.0, "uom": "EA", "type": "Pattern"},
            "FOAM-130": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-136": {"qty": 1.04, "uom": "EA", "type": "Foam"},
            "FOAM-132": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-125": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "POLB-129": {"qty": 1.0, "uom": "RL", "type": "Packaging"},
            "CTNS-118": {"qty": 1.0, "uom": "EA", "type": "Packaging"}
        }
    },
    "SBX-24545": {
        "description": "Moon Chair, Roast Natural F0262",
        "starbucksPartNum": "11174935",
        "quoteLine": "109209-4",
        "components": {
            "SBX-118": {"qty": 1.0, "uom": "EA", "type": "Frame"},
            "LEA-SBX16": {"qty": 55.0, "uom": "SQFT", "type": "Leather"},
            "FOAM-171": {"qty": 1.0, "uom": "EA", "type": "Pattern"},
            "FOAM-136": {"qty": 1.0, "uom": "EA", "type": "Foam"},
            "FOAM-130": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-125": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-132": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "POLB-129": {"qty": 1.0, "uom": "RL", "type": "Packaging"},
            "CTNS-117": {"qty": 1.0, "uom": "EA", "type": "Packaging"}
        }
    },
    "SBX-22880": {
        "description": "Comf Chair, Tan Brown F0245",
        "starbucksPartNum": "11174937",
        "quoteLine": "109209-3",
        "components": {
            "SBX-119": {"qty": 1.0, "uom": "EA", "type": "Frame"},
            "LEA-SBX15": {"qty": 90.0, "uom": "SQFT", "type": "Leather"},
            "FOAM-170": {"qty": 1.0, "uom": "EA", "type": "Pattern"},
            "FOAM-130": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-132": {"qty": 0.5, "uom": "EA", "type": "Foam"},
            "FOAM-125": {"qty": 0.33, "uom": "EA", "type": "Foam"},
            "POLB-129": {"qty": 1.0, "uom": "RL", "type": "Packaging"},
            "CTNS-118": {"qty": 1.0, "uom": "EA", "type": "Packaging"}
        }
    }
}


def get_all_components():
    """Extract all unique component part numbers from BOM"""
    components = set()
    for sku_data in MASTER_BOM.values():
        components.update(sku_data["components"].keys())
    return list(components)


def get_epicor_headers():
    """Build headers for Epicor REST API calls"""
    credentials = f"{EPICOR_CONFIG['username']}:{EPICOR_CONFIG['password']}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_creds}",
        "x-api-key": EPICOR_CONFIG['api_key'],
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def query_epicor_partwhse(part_num):
    """Query inventory for a specific part - tries PartWhses then falls back to PartCostSearches"""
    # First try PartSvc/PartWhses
    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartSvc/PartWhses"
        params = {
            "$filter": f"PartNum eq '{part_num}'",
            "$select": "PartNum,WarehouseCode,OnHandQty,AllocatedQty"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("value") and len(data["value"]) > 0:
                return data
    except requests.exceptions.RequestException as e:
        print(f"Error querying PartWhse for {part_num}: {e}")

    # Fallback: Use PartCostSearchSvc to get TotalQtyAvg (on-hand quantity for average costing)
    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartCostSearchSvc/PartCostSearches"
        params = {
            "$filter": f"PartNum eq '{part_num}'",
            "$top": "1",
            "$select": "PartNum,TotalQtyAvg"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("value") and len(data["value"]) > 0:
                qty = float(data["value"][0].get("TotalQtyAvg", 0) or 0)
                # Return synthetic warehouse record matching the format
                return {
                    "value": [{
                        "PartNum": part_num,
                        "WarehouseCode": "TOTAL",
                        "OnHandQty": qty,
                        "AllocatedQty": 0
                    }]
                }
    except requests.exceptions.RequestException as e:
        print(f"Error querying PartCostSearch for {part_num}: {e}")

    return None


def query_epicor_part(part_num):
    """Query part master info for description and UOM"""
    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartSvc/Parts"
        params = {
            "$filter": f"PartNum eq '{part_num}'",
            "$top": "1",
            "$select": "PartNum,PartDescription,IUM"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying Part for {part_num}: {e}")
        return None


def query_epicor_partbin(part_num):
    """Query inventory by bin for a specific part using PartSvc/PartBins"""
    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartSvc/PartBins"
        params = {
            "$filter": f"PartNum eq '{part_num}'",
            "$select": "PartNum,WarehouseCode,BinNum,OnhandQty"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying PartBin for {part_num}: {e}")
        return None


def query_epicor_open_pos(part_nums):
    """Query open purchase orders using POSvc/PORels"""
    try:
        # Build filter for multiple parts - use POSvc not PORelSvc
        part_filter = " or ".join([f"PartNum eq '{p}'" for p in part_nums])
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.POSvc/PORels"
        params = {
            "$filter": f"({part_filter}) and OpenRelease eq true",
            "$select": "PONum,POLine,PORelNum,PartNum,XRelQty,ReceivedQty,DueDate,PromiseDt",
            "$orderby": "DueDate"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying POs: {e}")
        return None


def query_epicor_baq(baq_name, params_dict=None):
    """Query a BAQ (Business Activity Query) in Epicor"""
    try:
        url = f"{EPICOR_CONFIG['base_url']}/BaqSvc/{baq_name}"
        response = requests.get(url, headers=get_epicor_headers(), params=params_dict, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying BAQ {baq_name}: {e}")
        return None


def fetch_part_inventory(part_num):
    """Fetch inventory and part info for a single part - used for parallel execution"""
    whse_result = query_epicor_partwhse(part_num)
    part_result = query_epicor_part(part_num)

    description = ""
    uom = "EA"
    if part_result and "value" in part_result and len(part_result["value"]) > 0:
        part_info = part_result["value"][0]
        description = part_info.get("PartDescription", "")
        uom = part_info.get("IUM", "EA")

    if whse_result and "value" in whse_result and len(whse_result["value"]) > 0:
        total_on_hand = sum(float(r.get("OnHandQty", 0) or 0) for r in whse_result["value"])
        total_allocated = sum(float(r.get("AllocatedQty", 0) or 0) for r in whse_result["value"])
        available = total_on_hand - total_allocated

        return {
            "partNum": part_num,
            "description": description,
            "onHand": total_on_hand,
            "allocated": total_allocated,
            "available": available,
            "uom": uom,
            "warehouses": [
                {
                    "warehouseCode": r.get("WarehouseCode", ""),
                    "onHand": float(r.get("OnHandQty", 0) or 0),
                    "allocated": float(r.get("AllocatedQty", 0) or 0)
                }
                for r in whse_result["value"]
            ],
            "error": None
        }
    else:
        return {
            "partNum": part_num,
            "description": description,
            "onHand": 0,
            "allocated": 0,
            "available": 0,
            "uom": uom,
            "warehouses": [],
            "error": "Failed to fetch inventory from Epicor"
        }


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Query current inventory from Epicor for all BOM components - REAL-TIME DATA ONLY"""
    components = get_all_components()
    inventory_data = {}
    errors = []

    # Use ThreadPoolExecutor for parallel requests (max 5 concurrent to avoid rate limiting)
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_part = {executor.submit(fetch_part_inventory, part): part for part in components}

        for future in as_completed(future_to_part):
            part_num = future_to_part[future]
            try:
                result = future.result()
                inventory_data[part_num] = result
                if result.get("error"):
                    errors.append(part_num)
            except Exception as e:
                print(f"Error fetching inventory for {part_num}: {e}")
                errors.append(part_num)
                inventory_data[part_num] = {
                    "partNum": part_num,
                    "description": "",
                    "onHand": 0,
                    "allocated": 0,
                    "available": 0,
                    "uom": "EA",
                    "warehouses": [],
                    "error": str(e)
                }

    return jsonify({
        "success": len(errors) == 0,
        "data": inventory_data,
        "timestamp": datetime.now().isoformat(),
        "source": "Epicor Kinetic REST API - Live",
        "errors": errors if errors else None
    })


@app.route('/api/pos', methods=['GET'])
def get_open_pos():
    """Query open purchase orders from Epicor for BOM components"""
    components = get_all_components()

    # Try querying the MRP_POs BAQ first
    baq_result = query_epicor_baq("MRP_POs")

    pos_data = {}

    if baq_result and "value" in baq_result:
        for record in baq_result["value"]:
            part_num = record.get("PODetail_PartNum", "")
            if part_num in components:
                if part_num not in pos_data:
                    pos_data[part_num] = []

                # Ensure numeric conversion - Epicor may return strings
                rel_qty = float(record.get("PORel_XRelQty", 0) or record.get("RelQty", 0) or 0)
                recv_qty = float(record.get("PORel_ReceivedQty", 0) or record.get("ReceivedQty", 0) or 0)

                pos_data[part_num].append({
                    "poNum": record.get("PORel_PONum", "") or record.get("PONum", ""),
                    "poLine": record.get("PORel_POLine", "") or record.get("POLine", ""),
                    "relNum": record.get("PORel_PORelNum", "") or record.get("PORelNum", ""),
                    "partNum": part_num,
                    "description": record.get("PODetail_LineDesc", "") or record.get("LineDesc", ""),
                    "vendorName": record.get("Vendor_Name", "") or record.get("VendorName", ""),
                    "orderQty": rel_qty,
                    "receivedQty": recv_qty,
                    "remainQty": rel_qty - recv_qty,
                    "uom": record.get("PORel_BaseUOM", "") or record.get("UOM", "EA"),
                    "dueDate": record.get("PORel_DueDate", "") or record.get("DueDate", ""),
                    "promiseDate": record.get("PORel_PromiseDt", "") or record.get("PromiseDt", ""),
                    "status": record.get("Calculated_Status", "Open")
                })
    else:
        # Fallback: Query PORels directly
        result = query_epicor_open_pos(components)
        if result and "value" in result:
            for record in result["value"]:
                part_num = record.get("PartNum", "")
                if part_num not in pos_data:
                    pos_data[part_num] = []

                # Ensure numeric conversion - Epicor may return strings
                rel_qty = float(record.get("XRelQty", 0) or record.get("RelQty", 0) or 0)
                recv_qty = float(record.get("ReceivedQty", 0) or 0)

                pos_data[part_num].append({
                    "poNum": record.get("PONum", ""),
                    "poLine": record.get("POLine", ""),
                    "relNum": record.get("PORelNum", ""),
                    "partNum": part_num,
                    "description": record.get("LineDesc", ""),
                    "vendorName": record.get("VendorName", ""),
                    "orderQty": rel_qty,
                    "receivedQty": recv_qty,
                    "remainQty": rel_qty - recv_qty,
                    "uom": "EA",
                    "dueDate": record.get("DueDate", ""),
                    "promiseDate": record.get("PromiseDt", ""),
                    "status": "Open"
                })

    return jsonify({
        "success": True,
        "data": pos_data,
        "timestamp": datetime.now().isoformat(),
        "source": "Epicor REST API"
    })


@app.route('/api/bom', methods=['GET'])
def get_bom():
    """Return master BOM structure"""
    return jsonify({
        "success": True,
        "data": MASTER_BOM,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/capacity', methods=['GET'])
def calculate_capacity():
    """Calculate production capacity using live Epicor data"""
    # Fetch live inventory
    inv_response = get_inventory()
    inv_data = inv_response.get_json()
    inventory = inv_data.get("data", {}) if inv_data.get("success") else {}

    # Fetch live POs
    pos_response = get_open_pos()
    pos_data_json = pos_response.get_json()
    pos = pos_data_json.get("data", {}) if pos_data_json.get("success") else {}

    results = {}
    total_current = 0
    total_future = 0
    blocked_count = 0

    for sku, sku_data in MASTER_BOM.items():
        bottlenecks = []

        for component, details in sku_data["components"].items():
            inv = inventory.get(component, {"available": 0, "onHand": 0, "allocated": 0})
            component_pos = pos.get(component, [])

            incoming_qty = sum(po.get("remainQty", 0) for po in component_pos)
            available = inv.get("available", 0)
            future_available = available + incoming_qty

            max_units_now = int(available / details["qty"]) if details["qty"] > 0 else 0
            max_units_future = int(future_available / details["qty"]) if details["qty"] > 0 else 0

            # Determine status
            if available <= 0:
                status = "critical"
            elif max_units_now < 10:
                status = "warning"
            else:
                status = "ok"

            bottlenecks.append({
                "component": component,
                "description": inv.get("description", ""),
                "qtyPer": details["qty"],
                "available": available,
                "onHand": inv.get("onHand", 0),
                "allocated": inv.get("allocated", 0),
                "incomingQty": incoming_qty,
                "futureAvailable": future_available,
                "maxUnitsNow": max_units_now,
                "maxUnitsFuture": max_units_future,
                "uom": details["uom"],
                "type": details["type"],
                "status": status,
                "pos": component_pos
            })

        # Find limiting components
        max_now = min(b["maxUnitsNow"] for b in bottlenecks) if bottlenecks else 0
        max_future = min(b["maxUnitsFuture"] for b in bottlenecks) if bottlenecks else 0

        limiting_now = next((b for b in bottlenecks if b["maxUnitsNow"] == max_now), None)
        limiting_future = next((b for b in bottlenecks if b["maxUnitsFuture"] == max_future), None)

        total_current += max_now
        total_future += max_future
        if max_now == 0:
            blocked_count += 1

        results[sku] = {
            **sku_data,
            "maxProductionNow": max_now,
            "maxProductionFuture": max_future,
            "limitingComponentNow": limiting_now["component"] if limiting_now else "UNKNOWN",
            "limitingComponentFuture": limiting_future["component"] if limiting_future else "UNKNOWN",
            "bottlenecks": bottlenecks,
            "isBlocked": max_now == 0
        }

    return jsonify({
        "success": True,
        "data": results,
        "summary": {
            "totalCurrentCapacity": total_current,
            "totalFutureCapacity": total_future,
            "blockedSkus": blocked_count,
            "totalSkus": len(MASTER_BOM)
        },
        "timestamp": datetime.now().isoformat(),
        "source": "Epicor REST API - Live Data"
    })


@app.route('/api/refresh', methods=['POST'])
def refresh_all_data():
    """Force refresh all data from Epicor"""
    return calculate_capacity()


@app.route('/')
def serve_dashboard():
    """Serve the main dashboard HTML"""
    return send_from_directory('.', 'starbucks_capacity_dashboard.html')


@app.route('/health')
def health_check():
    """Health check endpoint with Epicor connectivity test"""
    epicor_connected = False
    epicor_error = None

    try:
        # Test Epicor connection with a simple query
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartSvc/Parts"
        params = {"$top": 1, "$select": "PartNum"}
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=10)
        epicor_connected = response.status_code == 200
    except Exception as e:
        epicor_error = str(e)

    return jsonify({
        "status": "healthy" if epicor_connected else "degraded",
        "timestamp": datetime.now().isoformat(),
        "epicor": {
            "connected": epicor_connected,
            "endpoint": EPICOR_CONFIG["base_url"],
            "error": epicor_error
        }
    })


if __name__ == '__main__':
    print("=" * 60)
    print("  Starbucks Capacity Dashboard - Production Server")
    print("=" * 60)
    print(f"  Epicor Endpoint: {EPICOR_CONFIG['base_url']}")
    print(f"  Epicor User: {EPICOR_CONFIG['username']}")
    print("=" * 60)
    print("  Dashboard: http://localhost:5000")
    print("  Health:    http://localhost:5000/health")
    print("  API Endpoints:")
    print("    - GET  /api/inventory  - Live inventory from Epicor")
    print("    - GET  /api/pos        - Open POs from Epicor")
    print("    - GET  /api/bom        - Master BOM structure")
    print("    - GET  /api/capacity   - Calculated capacity (live)")
    print("    - POST /api/refresh    - Force data refresh")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
