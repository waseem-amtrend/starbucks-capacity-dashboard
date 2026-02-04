"""
Starbucks Capacity Dashboard - Backend Server
Queries Epicor REST API directly and serves data to frontend
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
from requests.auth import HTTPBasicAuth
import os
from datetime import datetime, timedelta
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__, static_folder='.')
CORS(app)

# Cache for part descriptions (they don't change frequently)
# This is for part master info only - inventory is always fetched fresh
PART_INFO_CACHE = {}
PART_CACHE_EXPIRY = timedelta(hours=1)  # Cache part descriptions for 1 hour

# Epicor REST API Configuration - v1 API
EPICOR_CONFIG = {
    "base_url": "https://centralusdtapp20.epicorsaas.com/SaaS704/api/v1",
    "username": os.environ.get("EPICOR_USERNAME", "Claude.AI"),
    "password": os.environ.get("EPICOR_PASSWORD", "@Mtrend2026"),
    "api_key": os.environ.get("EPICOR_API_KEY", "LgbgeQtNgh5GzbS27ZFpbeFigdJzQ4HEI6QpqBytRF8Xn"),
    "company": "28648"  # Company ID for authentication
}

# Master Quote Number for dynamic BOM fetching
MASTER_QUOTE_NUM = 109209

# Starbucks SKU mapping (Part Number -> Starbucks SKU)
STARBUCKS_SKU_MAP = {
    "SBX-22721": "11174933",  # Moon Chair, Fern Green
    "SBX-24545": "11174935",  # Moon Chair, Roast Natural
    "SBX-24540": "11174936",  # Comf Chair, Fern Green
    "SBX-22880": "11174937",  # Comf Chair, Tan Brown
    "SBX-24541": "11174939",  # Comf Chair, Roast Natural
}

# Component type classification (for UI display)
COMPONENT_TYPES = {
    "SBX-118": "Frame",
    "SBX-119": "Frame",
    "LEA-SBX14": "Leather",
    "LEA-SBX15": "Leather",
    "LEA-SBX16": "Leather",
    "FOAM-170": "Pattern",
    "FOAM-171": "Pattern",
    "FOAM-125": "Foam",
    "FOAM-130": "Foam",
    "FOAM-132": "Foam",
    "FOAM-136": "Foam",
    "POLB-129": "Packaging",
    "CTNS-117": "Packaging",
    "CTNS-118": "Packaging",
}

# UOM Conversions - parts where inventory UOM differs from consumption UOM
# Key: PartNum, Value: {inventoryUom, consumptionUom, conversionFactor, consumptionQtyPerUnit}
#
# POLB-129: Polybag 60" x 50CF - tracked in rolls (RL), but consumed as EA (1 bag per chair)
# - Inventory UOM: RL (Roll) - purchased and stocked in rolls
# - Roll contains: 100 bags (EA)
# - Consumption: 1 bag (EA) per chair
# - The BOM shows 1 RL per chair, but actually each chair only uses 1 bag from the roll
# - This is a BOM data issue - the BOM should say 0.01 RL or 1 EA per chair
# - We override the BOM qty per to 1 EA (1 bag per chair)
UOM_CONVERSIONS = {
    "POLB-129": {
        "inventoryUom": "RL",
        "consumptionUom": "EA",
        "conversionFactor": 100,  # 1 RL = 100 EA
        "overrideBomQtyPer": 1.0  # Each chair consumes 1 EA (bag), not 1 RL
    }
}

# Cache for BOM data (refreshed on demand or periodically)
BOM_CACHE = {}
BOM_CACHE_TIME = None
BOM_CACHE_EXPIRY = timedelta(minutes=30)  # Refresh BOM every 30 minutes


def fetch_quote_bom_from_epicor():
    """Fetch BOM dynamically from Epicor Quote 109209.
    Returns dict of SKU -> {description, starbucksPartNum, quoteLine, components}
    """
    global BOM_CACHE, BOM_CACHE_TIME

    # Return cached BOM if still valid
    if BOM_CACHE_TIME and (datetime.now() - BOM_CACHE_TIME) < BOM_CACHE_EXPIRY and BOM_CACHE:
        print("Using cached BOM data")
        return BOM_CACHE

    print(f"Fetching fresh BOM from Epicor Quote {MASTER_QUOTE_NUM}...")
    bom_data = {}

    try:
        # First get the quote lines to get parent part info
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.QuoteAsmSvc/QuoteAsms"
        params = {
            "$filter": f"QuoteNum eq {MASTER_QUOTE_NUM}",
            "$select": "QuoteNum,QuoteLine,AssemblySeq,PartNum,Description"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)

        if response.status_code != 200:
            print(f"Failed to fetch quote assemblies: {response.status_code}")
            return BOM_CACHE if BOM_CACHE else {}

        assemblies = response.json().get("value", [])

        # For each assembly (quote line), get the materials
        for asm in assemblies:
            quote_line = asm.get("QuoteLine")
            part_num = asm.get("PartNum", "")
            description = asm.get("Description", "")

            # Only process SBX parts (our finished goods)
            if not part_num.startswith("SBX-"):
                continue

            # Fetch materials for this quote line using GetByID
            mtl_url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.QuoteAsmSvc/GetByID"
            mtl_params = {
                "quoteNum": MASTER_QUOTE_NUM,
                "quoteLine": quote_line,
                "assemblySeq": 0
            }
            mtl_response = requests.get(mtl_url, headers=get_epicor_headers(), params=mtl_params, timeout=30)

            if mtl_response.status_code != 200:
                print(f"Failed to fetch materials for line {quote_line}: {mtl_response.status_code}")
                continue

            mtl_data = mtl_response.json()
            materials = mtl_data.get("returnObj", {}).get("QuoteMtl", [])

            # Build components dict
            components = {}
            for mtl in materials:
                mtl_part = mtl.get("PartNum", "")
                qty_per = float(mtl.get("QtyPer", 0) or 0)
                uom = mtl.get("IUM", "EA")

                # Get component type from classification
                comp_type = COMPONENT_TYPES.get(mtl_part, "Other")

                components[mtl_part] = {
                    "qty": qty_per,
                    "uom": uom,
                    "type": comp_type,
                    "mtlSeq": mtl.get("MtlSeq", 0)
                }

            # Add to BOM data
            bom_data[part_num] = {
                "description": description,
                "starbucksPartNum": STARBUCKS_SKU_MAP.get(part_num, ""),
                "quoteLine": f"{MASTER_QUOTE_NUM}-{quote_line}",
                "components": components
            }

        # Update cache
        BOM_CACHE = bom_data
        BOM_CACHE_TIME = datetime.now()
        print(f"BOM cache updated with {len(bom_data)} SKUs")

        return bom_data

    except Exception as e:
        print(f"Error fetching BOM from Epicor: {e}")
        return BOM_CACHE if BOM_CACHE else {}


def get_master_bom():
    """Get the master BOM - fetches from Epicor dynamically"""
    return fetch_quote_bom_from_epicor()


def get_all_components():
    """Extract all unique component part numbers from BOM"""
    bom = get_master_bom()
    components = set()
    for sku_data in bom.values():
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
    """Query part master info for description and UOM - uses cache for speed"""
    # Check cache first
    cache_entry = PART_INFO_CACHE.get(part_num)
    if cache_entry:
        cached_time, cached_data = cache_entry
        if datetime.now() - cached_time < PART_CACHE_EXPIRY:
            return cached_data

    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartSvc/Parts"
        params = {
            "$filter": f"PartNum eq '{part_num}'",
            "$top": "1",
            "$select": "PartNum,PartDescription,IUM"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        response.raise_for_status()
        result = response.json()

        # Cache the result
        PART_INFO_CACHE[part_num] = (datetime.now(), result)
        return result
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


# Global cache for job demands - refreshed per request cycle
JOB_DEMANDS_CACHE = {}
JOB_DEMANDS_CACHE_TIME = None

# Starbucks Customer Number - CustID 11-1000
STARBUCKS_CUST_NUM = 272


# Cache for Starbucks jobs (refreshed every 60 seconds)
STARBUCKS_JOBS_CACHE = set()
STARBUCKS_JOBS_CACHE_TIME = None


def get_starbucks_order_numbers():
    """Get set of order numbers for Starbucks customer (CustNum 272).
    Used to identify Starbucks jobs via job number pattern (OrderNum-Line-Release).
    """
    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.SalesOrderSvc/SalesOrders"
        params = {
            "$filter": f"CustNum eq {STARBUCKS_CUST_NUM} and OpenOrder eq true",
            "$select": "OrderNum",
            "$top": "500"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            orders = set(str(o.get("OrderNum", "")).zfill(6) for o in data.get("value", []) if o.get("OrderNum"))
            return orders
    except Exception as e:
        print(f"Error getting Starbucks orders: {e}")
    return set()


def get_starbucks_open_jobs():
    """Get list of open job numbers for Starbucks customer (CustNum 272).
    Returns set of job numbers like {'025043-1-1', '024189-1-1', ...}
    Uses two methods: XRefCustNum and job number pattern matching to order numbers.
    """
    global STARBUCKS_JOBS_CACHE, STARBUCKS_JOBS_CACHE_TIME

    # Return cached data if less than 60 seconds old
    if STARBUCKS_JOBS_CACHE_TIME and (datetime.now() - STARBUCKS_JOBS_CACHE_TIME).seconds < 60:
        return STARBUCKS_JOBS_CACHE

    all_jobs = set()

    try:
        # Method 1: Query jobs with XRefCustNum set to Starbucks
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.JobEntrySvc/JobEntries"
        params = {
            "$filter": f"XRefCustNum eq {STARBUCKS_CUST_NUM} and JobComplete eq false and JobClosed eq false",
            "$select": "JobNum",
            "$top": "500"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            jobs = set(j.get("JobNum", "") for j in data.get("value", []) if j.get("JobNum"))
            all_jobs.update(jobs)
            print(f"Found {len(jobs)} jobs via XRefCustNum")

        # Method 2: Get Starbucks open orders and match job numbers
        starbucks_orders = get_starbucks_order_numbers()
        if starbucks_orders:
            # Query all open jobs (ordered by most recent) and filter by order number pattern
            url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.JobEntrySvc/JobEntries"
            params = {
                "$filter": "JobComplete eq false and JobClosed eq false",
                "$select": "JobNum",
                "$orderby": "JobNum desc",  # Most recent jobs first
                "$top": "2000"  # Increase limit to get more jobs
            }
            response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                order_matched = 0
                for job in data.get("value", []):
                    job_num = job.get("JobNum", "")
                    # Job format: OrderNum-Line-Release (e.g., 025043-1-1)
                    if "-" in job_num:
                        order_part = job_num.split("-")[0]
                        if order_part in starbucks_orders:
                            all_jobs.add(job_num)
                            order_matched += 1
                print(f"Found {order_matched} additional jobs via order number matching")

        print(f"Total Starbucks jobs: {len(all_jobs)}")
        STARBUCKS_JOBS_CACHE = all_jobs
        STARBUCKS_JOBS_CACHE_TIME = datetime.now()
        return all_jobs

    except Exception as e:
        print(f"Error getting Starbucks jobs: {e}")

    return STARBUCKS_JOBS_CACHE if STARBUCKS_JOBS_CACHE else set()


def get_job_materials_via_getbyid(job_num):
    """Get job materials using GetByID method (OData entity query doesn't return materials).
    Returns tuple of (materials, job_prod_data) where job_prod_data contains order link info.
    """
    try:
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.JobEntrySvc/GetByID"
        params = {"jobNum": job_num}
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'returnObj' in data:
                materials = data['returnObj'].get('JobMtl', [])
                job_prods = data['returnObj'].get('JobProd', [])
                return (materials, job_prods)
    except Exception as e:
        print(f"Error getting materials for job {job_num}: {e}")
    return ([], [])


def query_all_job_demands(part_nums):
    """Query open job material demands for Starbucks orders only.
    Uses GetByID method since OData entity queries don't return job materials.
    Returns dict of part_num -> {totalDemand, jobCount, jobs}
    """
    global JOB_DEMANDS_CACHE, JOB_DEMANDS_CACHE_TIME

    # Cache job demands for 5 minutes to avoid repeated expensive queries
    if JOB_DEMANDS_CACHE_TIME and (datetime.now() - JOB_DEMANDS_CACHE_TIME).seconds < 300:
        return JOB_DEMANDS_CACHE

    results = {p: {"totalDemand": 0, "jobCount": 0, "jobs": []} for p in part_nums}
    part_nums_set = set(part_nums)

    try:
        # First get Starbucks job numbers
        starbucks_jobs = get_starbucks_open_jobs()
        if not starbucks_jobs:
            print("No Starbucks jobs found - no demands to track")
            JOB_DEMANDS_CACHE = results
            JOB_DEMANDS_CACHE_TIME = datetime.now()
            return results

        # Filter to only jobs that produce SBX parts (our finished goods)
        sbx_finished_goods = {'SBX-22721', 'SBX-22880', 'SBX-24540', 'SBX-24541', 'SBX-24545'}

        # Query jobs to get their part numbers
        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.JobEntrySvc/JobEntries"
        params = {
            "$filter": "JobComplete eq false and JobClosed eq false",
            "$select": "JobNum,PartNum",
            "$orderby": "JobNum desc",
            "$top": "2000"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)
        job_parts = {}
        if response.status_code == 200:
            for job in response.json().get("value", []):
                job_parts[job.get("JobNum", "")] = job.get("PartNum", "")

        # Filter Starbucks jobs to only SBX finished goods
        sbx_jobs = [j for j in starbucks_jobs if job_parts.get(j, "") in sbx_finished_goods]
        print(f"Found {len(sbx_jobs)} Starbucks SBX jobs to check for materials")

        # Query materials for each SBX job using GetByID (limited to avoid timeout)
        # Process in parallel for speed
        def process_job(job_num):
            materials, _ = get_job_materials_via_getbyid(job_num)
            job_demands = []
            for mtl in materials:
                part_num = mtl.get("PartNum", "")
                if part_num in part_nums_set:
                    required = float(mtl.get("RequiredQty", 0) or 0)
                    issued = float(mtl.get("IssuedQty", 0) or 0)
                    remaining = max(0, required - issued)
                    if remaining > 0:
                        job_demands.append({
                            "partNum": part_num,
                            "jobNum": job_num,
                            "required": required,
                            "issued": issued,
                            "remaining": remaining
                        })
            return job_demands

        # Process most recent jobs in parallel (limit to 30 jobs to avoid timeout)
        # Sort by job number descending to get most recent first
        recent_sbx_jobs = sorted(sbx_jobs, reverse=True)[:30]
        print(f"Processing {len(recent_sbx_jobs)} most recent SBX jobs for materials")

        all_demands = []
        with ThreadPoolExecutor(max_workers=15) as executor:  # Increased parallelism
            futures = {executor.submit(process_job, job): job for job in recent_sbx_jobs}
            for future in as_completed(futures):
                demands = future.result()
                all_demands.extend(demands)

        # Aggregate demands by part
        for demand in all_demands:
            part_num = demand["partNum"]
            if part_num in results:
                results[part_num]["totalDemand"] += demand["remaining"]
                results[part_num]["jobs"].append({
                    "jobNum": demand["jobNum"],
                    "required": demand["required"],
                    "issued": demand["issued"],
                    "remaining": demand["remaining"]
                })

        # Calculate job counts
        for part_num in results:
            results[part_num]["jobCount"] = len(results[part_num]["jobs"])

        total_demand = sum(r["totalDemand"] for r in results.values())
        print(f"Total material demands found: {total_demand}")

        JOB_DEMANDS_CACHE = results
        JOB_DEMANDS_CACHE_TIME = datetime.now()
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error querying batch job demands: {e}")
        return results


def query_epicor_job_demands(part_num):
    """Query open job material demands for a specific part (uses cache from batch query)."""
    # This is now just a lookup from the batch cache
    if JOB_DEMANDS_CACHE and part_num in JOB_DEMANDS_CACHE:
        return JOB_DEMANDS_CACHE[part_num]
    return {"totalDemand": 0, "jobCount": 0, "jobs": []}


def apply_uom_conversion(part_num, qty, from_uom):
    """Apply UOM conversion for parts that have different inventory vs consumption UOMs.
    Returns tuple of (converted_qty, converted_uom, conversion_applied)
    """
    if part_num in UOM_CONVERSIONS:
        conv = UOM_CONVERSIONS[part_num]
        if from_uom == conv["inventoryUom"]:
            # Convert from inventory UOM to consumption UOM
            converted_qty = qty * conv["conversionFactor"]
            return (converted_qty, conv["consumptionUom"], True)
    return (qty, from_uom, False)


def fetch_part_inventory(part_num):
    """Fetch inventory, part info, and job demands for a single part - used for parallel execution"""
    whse_result = query_epicor_partwhse(part_num)
    part_result = query_epicor_part(part_num)
    demand_result = query_epicor_job_demands(part_num)

    description = ""
    uom = "EA"
    if part_result and "value" in part_result and len(part_result["value"]) > 0:
        part_info = part_result["value"][0]
        description = part_info.get("PartDescription", "")
        uom = part_info.get("IUM", "EA")

    # Get job demand (committed to open jobs)
    job_demand = 0
    job_count = 0
    if demand_result:
        job_demand = demand_result.get("totalDemand", 0)
        job_count = len(demand_result.get("jobs", []))

    if whse_result and "value" in whse_result and len(whse_result["value"]) > 0:
        total_on_hand = sum(float(r.get("OnHandQty", 0) or 0) for r in whse_result["value"])
        total_allocated = sum(float(r.get("AllocatedQty", 0) or 0) for r in whse_result["value"])

        # True available = On Hand - Allocated (from Epicor) - Job Demands (uncommitted material)
        # Note: Epicor's AllocatedQty may or may not include job demands depending on config
        # We add jobDemand separately to be safe and transparent
        available = total_on_hand - total_allocated
        true_available = max(0, available - job_demand)

        # Apply UOM conversion if needed (e.g., POLB-129: 1 RL = 100 EA)
        # NOTE: Inventory is in stocking UOM (RL), but job demands are already in consumption UOM (EA)
        # So we only convert inventory quantities, NOT job demands
        inventory_uom = uom
        converted_on_hand, display_uom, conversion_applied = apply_uom_conversion(part_num, total_on_hand, uom)
        converted_allocated, _, _ = apply_uom_conversion(part_num, total_allocated, uom)
        # Job demands are already in consumption UOM (EA) from Epicor, don't convert
        converted_job_demand = job_demand
        # Recalculate available and true available after conversion
        converted_available = converted_on_hand - converted_allocated
        converted_true_available = max(0, converted_available - converted_job_demand)

        return {
            "partNum": part_num,
            "description": description,
            "onHand": converted_on_hand,
            "allocated": converted_allocated,
            "jobDemand": converted_job_demand,
            "jobCount": job_count,
            "available": converted_available,
            "trueAvailable": converted_true_available,
            "uom": display_uom,  # Display in consumption UOM (EA for POLB-129)
            "inventoryUom": inventory_uom,  # Original inventory UOM
            "conversionApplied": conversion_applied,
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
            "jobDemand": job_demand,
            "jobCount": job_count,
            "available": 0,
            "trueAvailable": 0,
            "uom": uom,
            "inventoryUom": uom,
            "conversionApplied": False,
            "warehouses": [],
            "error": "Failed to fetch inventory from Epicor"
        }


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Query current inventory from Epicor for all BOM components - REAL-TIME DATA ONLY"""
    components = get_all_components()
    inventory_data = {}
    errors = []

    # Pre-fetch all job demands in batch (2 API calls instead of 2 per part)
    query_all_job_demands(components)

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
    """Return master BOM structure - fetched dynamically from Epicor"""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    if force_refresh:
        global BOM_CACHE_TIME
        BOM_CACHE_TIME = None  # Force cache invalidation

    bom = get_master_bom()
    return jsonify({
        "success": True,
        "data": bom,
        "timestamp": datetime.now().isoformat(),
        "source": f"Epicor Quote {MASTER_QUOTE_NUM}",
        "cacheTime": BOM_CACHE_TIME.isoformat() if BOM_CACHE_TIME else None
    })


@app.route('/api/capacity', methods=['GET'])
def calculate_capacity():
    """Calculate production capacity using live Epicor data"""
    # Get the dynamic BOM from Epicor
    master_bom = get_master_bom()

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

    for sku, sku_data in master_bom.items():
        bottlenecks = []

        for component, details in sku_data["components"].items():
            inv = inventory.get(component, {"available": 0, "trueAvailable": 0, "onHand": 0, "allocated": 0, "jobDemand": 0, "jobCount": 0})
            component_pos = pos.get(component, [])

            incoming_qty = sum(po.get("remainQty", 0) for po in component_pos)

            # Use trueAvailable (which accounts for job demands) for capacity calculation
            available = inv.get("available", 0)  # Raw available (onHand - allocated)
            true_available = inv.get("trueAvailable", available)  # After subtracting job demands
            job_demand = inv.get("jobDemand", 0)
            job_count = inv.get("jobCount", 0)

            # Apply UOM conversion to incoming PO quantities if needed
            # POs may be in inventory UOM (RL) but we need consumption UOM (EA)
            if component in UOM_CONVERSIONS:
                conv = UOM_CONVERSIONS[component]
                # Convert incoming PO qty from inventory UOM to consumption UOM
                incoming_qty = incoming_qty * conv["conversionFactor"]

            # Future available is based on true available + incoming POs
            future_available = true_available + incoming_qty

            # Get BOM qty per unit - this is in the BOM UOM (e.g., 1 RL for POLB-129)
            bom_qty_per = details["qty"]
            bom_uom = details["uom"]

            # For capacity calculation, we need to handle UOM conversions
            # Example: POLB-129 BOM says 1 RL per chair, but actually each chair uses 1 bag (EA)
            # The BOM is incorrect - it should say 0.01 RL or 1 EA per chair
            # We override with the correct consumption qty per unit
            effective_qty_per = bom_qty_per
            display_uom = bom_uom
            if component in UOM_CONVERSIONS:
                conv = UOM_CONVERSIONS[component]
                # If there's an override for BOM qty per, use it
                if "overrideBomQtyPer" in conv:
                    effective_qty_per = conv["overrideBomQtyPer"]
                    display_uom = conv["consumptionUom"]
                elif bom_uom == conv["inventoryUom"]:
                    # Convert BOM qty from inventory UOM to consumption UOM
                    effective_qty_per = bom_qty_per * conv["conversionFactor"]
                    display_uom = conv["consumptionUom"]

            # Calculate capacity using TRUE available (after job demands) and effective qty per
            max_units_now = int(true_available / effective_qty_per) if effective_qty_per > 0 else 0
            max_units_future = int(future_available / effective_qty_per) if effective_qty_per > 0 else 0

            # Determine status based on true available
            if true_available <= 0:
                status = "critical"
            elif max_units_now < 10:
                status = "warning"
            else:
                status = "ok"

            bottlenecks.append({
                "component": component,
                "description": inv.get("description", ""),
                "qtyPer": effective_qty_per,  # Qty per in consumption UOM
                "bomQtyPer": bom_qty_per,  # Original BOM qty per
                "bomUom": bom_uom,  # Original BOM UOM
                "available": available,  # Raw available (before job demands)
                "trueAvailable": true_available,  # After job demands
                "jobDemand": job_demand,  # Qty committed to open jobs
                "jobCount": job_count,  # Number of jobs
                "onHand": inv.get("onHand", 0),
                "allocated": inv.get("allocated", 0),
                "incomingQty": incoming_qty,
                "futureAvailable": future_available,
                "maxUnitsNow": max_units_now,
                "maxUnitsFuture": max_units_future,
                "uom": display_uom,  # Display in consumption UOM
                "type": details["type"],
                "status": status,
                "conversionApplied": component in UOM_CONVERSIONS
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
            "totalSkus": len(master_bom)
        },
        "timestamp": datetime.now().isoformat(),
        "source": f"Epicor REST API - Live Data (Quote {MASTER_QUOTE_NUM})"
    })


@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get material transaction history for Starbucks BOM parts.
    Query params:
        part_num: Filter by specific part (optional)
        days_back: Number of days of history (default 30)
    """
    part_num = request.args.get('part_num')
    days_back = int(request.args.get('days_back', 30))

    try:
        # Build filter for transaction query
        filters = []

        if part_num:
            # Single part filter
            filters.append(f"PartNum eq '{part_num}'")
        else:
            # Filter by all BOM component parts
            components = get_all_components()
            part_filter = " or ".join([f"PartNum eq '{p}'" for p in components])
            filters.append(f"({part_filter})")

        # Date filter - last N days (use OData datetime literal format)
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        filters.append(f"TranDate ge datetime'{from_date}T00:00:00'")

        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.PartTranSvc/PartTrans"
        params = {
            "$filter": " and ".join(filters),
            "$select": "TranDate,TranType,TranQty,JobNum,PartNum,WareHouseCode,EntryPerson,TranReference,PartDescription",
            "$orderby": "TranDate desc",
            "$top": "500"
        }

        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=60)

        if response.status_code != 200:
            error_detail = ""
            try:
                error_detail = response.text[:500]
            except:
                pass
            print(f"Epicor transactions API error: {response.status_code} - {error_detail}")
            return jsonify({
                "success": False,
                "error": f"Epicor API error: {response.status_code}",
                "detail": error_detail,
                "timestamp": datetime.now().isoformat()
            })

        data = response.json()
        transactions = []

        for record in data.get("value", []):
            tran_type = record.get("TranType", "")
            # Classify transaction type for UI display
            if tran_type in ["STK-MTL", "MTL-STK"]:
                type_label = "Issue to Job" if tran_type == "STK-MTL" else "Return from Job"
                type_class = "issue"
            elif tran_type in ["PUR-STK", "REC-STK"]:
                type_label = "Receipt"
                type_class = "receipt"
            elif tran_type in ["ADJ-QTY", "ADJ-CST"]:
                type_label = "Adjustment"
                type_class = "adjustment"
            else:
                type_label = tran_type
                type_class = "other"

            transactions.append({
                "date": record.get("TranDate", ""),
                "type": tran_type,
                "typeLabel": type_label,
                "typeClass": type_class,
                "qty": float(record.get("TranQty", 0) or 0),
                "jobNum": record.get("JobNum", ""),
                "partNum": record.get("PartNum", ""),
                "partDescription": record.get("PartDescription", ""),
                "warehouse": record.get("WareHouseCode", ""),
                "entryPerson": record.get("EntryPerson", ""),
                "reference": record.get("TranReference", "")
            })

        return jsonify({
            "success": True,
            "data": transactions,
            "count": len(transactions),
            "filter": {
                "partNum": part_num,
                "daysBack": days_back
            },
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@app.route('/api/job-materials', methods=['GET'])
def get_job_materials():
    """Get all open Starbucks SBX jobs with their material status.
    Shows which materials have been issued vs required for each job.
    """
    try:
        # Get open Starbucks jobs
        starbucks_jobs = get_starbucks_open_jobs()
        if not starbucks_jobs:
            return jsonify({
                "success": True,
                "data": [],
                "count": 0,
                "timestamp": datetime.now().isoformat()
            })

        # Get job details to filter only SBX finished goods
        sbx_finished_goods = {'SBX-22721', 'SBX-22880', 'SBX-24540', 'SBX-24541', 'SBX-24545'}

        url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.JobEntrySvc/JobEntries"
        params = {
            "$filter": "JobComplete eq false and JobClosed eq false",
            "$select": "JobNum,PartNum,PartDescription,ProdQty,StartDate,ReqDueDate",
            "$orderby": "JobNum desc",
            "$top": "500"
        }
        response = requests.get(url, headers=get_epicor_headers(), params=params, timeout=30)

        job_info = {}
        if response.status_code == 200:
            for job in response.json().get("value", []):
                job_info[job.get("JobNum", "")] = job

        # Ship dates will be fetched per-job from JobProd in the card processing
        job_ship_dates = {}

        # Filter to SBX jobs only
        sbx_jobs = [j for j in starbucks_jobs if job_info.get(j, {}).get("PartNum", "") in sbx_finished_goods]

        # Get materials for each job (limit to most recent 50 to avoid timeout)
        recent_jobs = sorted(sbx_jobs, reverse=True)[:50]

        job_cards = []

        def process_job_for_card(job_num):
            """Get job materials and build card data"""
            materials, job_prods = get_job_materials_via_getbyid(job_num)
            info = job_info.get(job_num, {})

            material_rows = []
            total_required = 0
            total_issued = 0

            for mtl in materials:
                required = float(mtl.get("RequiredQty", 0) or 0)
                issued = float(mtl.get("IssuedQty", 0) or 0)
                total_required += required
                total_issued += issued

                # Determine status
                if issued >= required and required > 0:
                    status = "complete"
                elif issued > 0:
                    status = "partial"
                else:
                    status = "missing"

                material_rows.append({
                    "partNum": mtl.get("PartNum", ""),
                    "required": required,
                    "issued": issued,
                    "remaining": max(0, required - issued),
                    "status": status,
                    "uom": mtl.get("IUM", "EA")
                })

            # Overall job status
            if total_issued >= total_required and total_required > 0:
                job_status = "complete"
            elif total_issued > 0:
                job_status = "partial"
            else:
                job_status = "missing"

            # Get ship-by date from JobProd -> OrderRel
            ship_by_date = ""
            if job_prods:
                # JobProd contains OrderNum, OrderLine, OrderRelNum - use these to get NeedByDate
                first_prod = job_prods[0] if job_prods else {}
                order_num = first_prod.get("OrderNum")
                order_line = first_prod.get("OrderLine")
                order_rel = first_prod.get("OrderRelNum", 1)

                if order_num and order_line:
                    try:
                        # Query OrderRel for NeedByDate
                        order_rel_url = f"{EPICOR_CONFIG['base_url']}/Erp.BO.SalesOrderSvc/OrderRels"
                        order_rel_params = {
                            "$filter": f"OrderNum eq {order_num} and OrderLine eq {order_line} and OrderRelNum eq {order_rel}",
                            "$select": "NeedByDate,ReqDate",
                            "$top": "1"
                        }
                        order_rel_resp = requests.get(order_rel_url, headers=get_epicor_headers(), params=order_rel_params, timeout=10)
                        if order_rel_resp.status_code == 200:
                            order_rels = order_rel_resp.json().get("value", [])
                            if order_rels:
                                ship_by_date = order_rels[0].get("NeedByDate", "") or order_rels[0].get("ReqDate", "")
                    except Exception as e:
                        print(f"Error getting ship date for job {job_num}: {e}")

            return {
                "jobNum": job_num,
                "partNum": info.get("PartNum", ""),
                "partDescription": info.get("PartDescription", ""),
                "prodQty": float(info.get("ProdQty", 0) or 0),
                "startDate": info.get("StartDate", ""),
                "dueDate": info.get("ReqDueDate", ""),
                "shipByDate": ship_by_date,
                "materials": material_rows,
                "materialCount": len(material_rows),
                "status": job_status
            }

        # Process jobs in parallel for speed
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_job_for_card, job): job for job in recent_jobs}
            for future in as_completed(futures):
                try:
                    card = future.result()
                    if card["materials"]:  # Only include jobs with materials
                        job_cards.append(card)
                except Exception as e:
                    print(f"Error processing job: {e}")

        # Sort by job number descending
        job_cards.sort(key=lambda x: x["jobNum"], reverse=True)

        return jsonify({
            "success": True,
            "data": job_cards,
            "count": len(job_cards),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error fetching job materials: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@app.route('/api/refresh', methods=['POST'])
def refresh_all_data():
    """Force refresh all data from Epicor including BOM"""
    global BOM_CACHE_TIME, JOB_DEMANDS_CACHE_TIME
    # Invalidate caches to force fresh data
    BOM_CACHE_TIME = None
    JOB_DEMANDS_CACHE_TIME = None
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
        },
        "cache": {
            "partInfoCached": len(PART_INFO_CACHE)
        }
    })


def preload_all_caches_background():
    """Preload all caches in background thread - doesn't block server startup"""
    import threading
    import time

    def load_all():
        time.sleep(5)  # Wait for server to be fully ready and pass health checks
        try:
            # Preload part cache first
            components = get_all_components()
            print(f"Background: Preloading part info cache for {len(components)} components...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(query_epicor_part, part): part for part in components}
                for future in as_completed(futures):
                    part = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error preloading {part}: {e}")
            print(f"Background: Part cache preloaded with {len(PART_INFO_CACHE)} parts")

            # Then preload job demands
            print("Background: Preloading job demands...")
            query_all_job_demands(components)
            print("Background: Job demands preloaded successfully")
        except Exception as e:
            print(f"Background: Error preloading caches: {e}")

    thread = threading.Thread(target=load_all, daemon=True)
    thread.start()


# Start background preload (non-blocking - server starts immediately)
preload_all_caches_background()


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
