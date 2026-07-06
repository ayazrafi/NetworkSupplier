import os
import math
import time
import uuid
import datetime
import threading
import random
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# MongoDB connection string configured for localhost:27018
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mfimongomaster:mongomongo%26*(@localhost:27018/")
DB_NAME = os.environ.get("MONGO_DB", "supplier_network")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
db = client[DB_NAME]
nodes_collection = db["nodes"]
jobs_collection = db["jobs"]

db_available = True
try:
    client.server_info()  # Ping the database
    print(f"Connected to MongoDB at {MONGO_URI}")
except Exception as e:
    print(f"WARNING: Could not connect to MongoDB. Falling back to in-memory storage. Error: {e}")
    db_available = False

in_memory_jobs = []
public_osrm_failed = False

MAX_DISTANCE_LIMIT = 2000.0

DEFAULT_NODES = [
    { 
        "id": "F1", 
        "name": "Anand Cooperatives", 
        "type": "farmer", 
        "products": [
            { "type": "Cow Milk", "supply": 6000 },
            { "type": "Buffalo Milk", "supply": 4000 }
        ],
        "lat": 22.5645, 
        "lng": 72.9289 
    },
    { 
        "id": "F2", 
        "name": "Nadiad Farmers", 
        "type": "farmer", 
        "products": [
            { "type": "Cow Milk", "supply": 4000 }
        ],
        "lat": 22.6916, 
        "lng": 72.8634 
    },
    { 
        "id": "F3", 
        "name": "Kheda Milk Union", 
        "type": "farmer", 
        "products": [
            { "type": "Buffalo Milk", "supply": 5000 }
        ],
        "lat": 22.7533, 
        "lng": 72.6819 
    },
    { 
        "id": "H1", 
        "name": "BMC Nadiad", 
        "type": "hub", 
        "subtype": "BMC", 
        "products": [
            { "type": "Cow Milk", "capacity": 7000, "processing_cost": 0.15 },
            { "type": "Buffalo Milk", "capacity": 5000, "processing_cost": 0.20 }
        ],
        "lat": 22.6700, 
        "lng": 72.8800 
    },
    { 
        "id": "H2", 
        "name": "MCC Kheda", 
        "type": "hub", 
        "subtype": "MCC", 
        "products": [
            { "type": "Cow Milk", "capacity": 8000, "processing_cost": 0.20 }
        ],
        "lat": 22.7200, 
        "lng": 72.7100 
    },
    { 
        "id": "P1", 
        "name": "Amul Cheese Plant", 
        "type": "plant", 
        "inflow_milks": [
            { "type": "Cow Milk", "capacity": 8000, "processing_cost": 0.50 },
            { "type": "Buffalo Milk", "capacity": 6000, "processing_cost": 0.60 }
        ],
        "products": [
            { "type": "Cow Cheese", "yield": 0.10 }, 
            { "type": "Cow Liquid Milk", "yield": 1.0 },
            { "type": "Buffalo Cheese", "yield": 0.10 }
        ], 
        "capacity": 10000, 
        "processing_cost": 0.60, 
        "lat": 22.5800, 
        "lng": 72.9500 
    },
    { 
        "id": "P2", 
        "name": "Anand Dairy", 
        "type": "plant", 
        "inflow_milks": [
            { "type": "Cow Milk", "capacity": 9000, "processing_cost": 0.40 },
            { "type": "Buffalo Milk", "capacity": 5000, "processing_cost": 0.50 }
        ],
        "products": [
            { "type": "Cow Liquid Milk", "yield": 1.0 }, 
            { "type": "Cow Khoya", "yield": 0.20 }, 
            { "type": "Buffalo Butter", "yield": 0.06 }
        ], 
        "capacity": 12000, 
        "processing_cost": 0.40, 
        "lat": 22.5400, 
        "lng": 72.9100 
    },
    { 
        "id": "G1", 
        "name": "Ahmedabad Metro", 
        "type": "geography", 
        "products": [
            { "type": "Cow Liquid Milk", "demand": 8000, "price": 60.00 }, 
            { "type": "Cow Cheese", "demand": 400, "price": 700.00 }
        ], 
        "lat": 23.0225, 
        "lng": 72.5714 
    },
    { 
        "id": "G2", 
        "name": "Vadodara City", 
        "type": "geography", 
        "products": [
            { "type": "Buffalo Cheese", "demand": 600, "price": 750.00 }, 
            { "type": "Buffalo Butter", "demand": 150, "price": 550.00 }
        ], 
        "lat": 22.3072, 
        "lng": 73.1812 
    },
    { 
        "id": "G3", 
        "name": "Nadiad Market", 
        "type": "geography", 
        "products": [
            { "type": "Cow Khoya", "demand": 400, "price": 400.00 }, 
            { "type": "Cow Liquid Milk", "demand": 2000, "price": 60.00 }
        ], 
        "lat": 22.6948, 
        "lng": 72.8223 
    },
    { 
        "id": "G4", 
        "name": "Kheda Town", 
        "type": "geography", 
        "products": [
            { "type": "Buffalo Butter", "demand": 180, "price": 550.00 }, 
            { "type": "Cow Milk Powder", "demand": 100, "price": 420.00 }
        ], 
        "lat": 22.7580, 
        "lng": 72.6850 
    }
]

in_memory_nodes = list(DEFAULT_NODES)

# Seed MongoDB with default nodes if it is empty
if db_available:
    try:
        if nodes_collection.count_documents({}) == 0:
            nodes_collection.insert_many(DEFAULT_NODES)
            print("Successfully seeded MongoDB with default nodes.")
    except Exception as e:
        print(f"Error seeding MongoDB: {e}")
        db_available = False


# Helper function to compute Haversine distance in kilometers
def calculate_haversine_distance(node1, node2):
    R = 6371.0  # Earth's radius in kilometers
    
    lat1 = math.radians(node1.get('lat', 0.0))
    lon1 = math.radians(node1.get('lng', 0.0))
    lat2 = math.radians(node2.get('lat', 0.0))
    lon2 = math.radians(node2.get('lng', 0.0))
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

import urllib.request
import json

_distance_cache = {}
local_osrm_5002_failed = False
local_osrm_5000_failed = False

# Compute actual road path distance using self-hosted or free public OSRM routing engine
def get_road_distance(node1, node2):
    global local_osrm_5002_failed, local_osrm_5000_failed
    pair_key = tuple(sorted([node1.get('id'), node2.get('id')]))
    if pair_key in _distance_cache:
        return _distance_cache[pair_key]
        
    lat1 = node1.get('lat', 0.0)
    lon1 = node1.get('lng', 0.0)
    lat2 = node2.get('lat', 0.0)
    lon2 = node2.get('lng', 0.0)
    
    # Check local OSRM services (port 5002 or 5000), then public OSRM demo API
    urls = []
    if not local_osrm_5002_failed:
        urls.append((5002, f"http://localhost:5002/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"))
    if not local_osrm_5000_failed:
        urls.append((5000, f"http://localhost:5000/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"))
    if not public_osrm_failed:
        urls.append((80, f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"))
        
    h_dist = calculate_haversine_distance(node1, node2)
    
    for port, url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GeoFlowOptimizer'})
            # Localhost is instant, public might take slightly longer
            timeout_val = 0.3 if port in (5002, 5000) else 1.5
            with urllib.request.urlopen(req, timeout=timeout_val) as response:
                res_data = json.loads(response.read().decode())
                if res_data.get('code') == 'Ok' and res_data.get('routes'):
                    dist = res_data['routes'][0]['distance'] / 1000.0
                    # Sanity check: if OSRM returned 0/near-zero distance but Haversine distance is > 1.0 km,
                    # it means OSRM snapped to the same boundary node due to limited local map extract.
                    if dist < 0.1 and h_dist > 1.0:
                        continue
                    _distance_cache[pair_key] = dist
                    return dist
        except Exception as e:
            if port == 5002:
                print(f"Local OSRM on port 5002 failed: {e}. Latch-failing it.")
                local_osrm_5002_failed = True
            elif port == 5000:
                print(f"Local OSRM on port 5000 failed: {e}. Latch-failing it.")
                local_osrm_5000_failed = True
            continue
            
    # Fallback to straight-line Haversine distance
    fallback_dist = h_dist
    _distance_cache[pair_key] = fallback_dist
    return fallback_dist


# Directory setup for Excel jobs
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# OSRM Table API helper to fetch road distances in bulk for candidate pairs
def get_osrm_distances_for_candidates(source_node, candidate_nodes):
    global public_osrm_failed, local_osrm_5002_failed, local_osrm_5000_failed
    coords = [f"{source_node['lng']},{source_node['lat']}"]
    for c in candidate_nodes:
        coords.append(f"{c['lng']},{c['lat']}")
        
    coords_str = ";".join(coords)
    sources = "0"
    destinations = ";".join(str(i) for i in range(1, len(coords)))
    
    # Try local OSRM table endpoints
    local_urls = []
    if not local_osrm_5002_failed:
        local_urls.append((5002, f"http://localhost:5002/table/v1/driving/{coords_str}?sources={sources}&destinations={destinations}&annotations=distance"))
    if not local_osrm_5000_failed:
        local_urls.append((5000, f"http://localhost:5000/table/v1/driving/{coords_str}?sources={sources}&destinations={destinations}&annotations=distance"))
        
    for port, url in local_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GeoFlowOptimizer'})
            with urllib.request.urlopen(req, timeout=0.3) as response:
                res_data = json.loads(response.read().decode())
                if res_data.get('code') == 'Ok' and 'distances' in res_data:
                    row_distances = res_data['distances'][0]
                    # Check if any distance returned is invalid (0.0 but Haversine > 1.0)
                    results = {}
                    has_invalid = False
                    for idx, c in enumerate(candidate_nodes):
                        val = row_distances[idx]
                        h_dist = calculate_haversine_distance(source_node, c)
                        if val is not None:
                            val_km = val / 1000.0
                            if val_km < 0.1 and h_dist > 1.0:
                                has_invalid = True
                                break
                            results[c['id']] = val_km
                        else:
                            results[c['id']] = h_dist
                    if not has_invalid:
                        # Write to global cache
                        for idx, c in enumerate(candidate_nodes):
                            val = row_distances[idx]
                            h_dist = calculate_haversine_distance(source_node, c)
                            pair_key = tuple(sorted([source_node['id'], c['id']]))
                            _distance_cache[pair_key] = val / 1000.0 if val is not None else h_dist
                        return results
                    else:
                        print(f"Local OSRM on port {port} returned snapped/invalid distances. Latch-failing it.")
                        if port == 5002:
                            local_osrm_5002_failed = True
                        elif port == 5000:
                            local_osrm_5000_failed = True
        except Exception as e:
            print(f"Local OSRM table on port {port} failed: {e}. Latch-failing it.")
            if port == 5002:
                local_osrm_5002_failed = True
            elif port == 5000:
                local_osrm_5000_failed = True
            continue
            
    # Try public OSRM Table API (if not latch-failed)
    if not public_osrm_failed:
        url = f"https://router.project-osrm.org/table/v1/driving/{coords_str}?sources={sources}&destinations={destinations}&annotations=distance"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GeoFlowOptimizer'})
            with urllib.request.urlopen(req, timeout=1.0) as response:
                res_data = json.loads(response.read().decode())
                if res_data.get('code') == 'Ok' and 'distances' in res_data:
                    row_distances = res_data['distances'][0]
                    results = {}
                    for idx, c in enumerate(candidate_nodes):
                        val = row_distances[idx]
                        h_dist = calculate_haversine_distance(source_node, c)
                        pair_key = tuple(sorted([source_node['id'], c['id']]))
                        if val is not None:
                            val_km = val / 1000.0
                            if val_km < 0.1 and h_dist > 1.0:
                                _distance_cache[pair_key] = h_dist
                                results[c['id']] = h_dist
                            else:
                                _distance_cache[pair_key] = val_km
                                results[c['id']] = val_km
                        else:
                            _distance_cache[pair_key] = h_dist
                            results[c['id']] = h_dist
                    return results
        except Exception as e:
            print("Public OSRM Table API failed or rate-limited. Falling back to Haversine.", e)
            public_osrm_failed = True
            
    # Haversine fallback for all candidates
    fallback_results = {}
    for c in candidate_nodes:
        h_dist = calculate_haversine_distance(source_node, c)
        pair_key = tuple(sorted([source_node['id'], c['id']]))
        _distance_cache[pair_key] = h_dist
        fallback_results[c['id']] = h_dist
    return fallback_results


# Excel random network generator containing 1000 nodes and UUID network_id
def generate_random_network():
    network_id = str(uuid.uuid4())
    rows = []
    
    # 300 Farmers
    for i in range(1, 301):
        lat = round(random.uniform(21.5, 23.5), 4)
        lng = round(random.uniform(71.0, 73.5), 4)
        # Cow Milk
        rows.append({
            'node_id': f"F{i}",
            'name': f"Farmer {i}",
            'type': 'farmer',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Milk',
            'supply': random.randint(1000, 8000),
            'network_id': network_id
        })
        # Buffalo Milk
        rows.append({
            'node_id': f"F{i}",
            'name': f"Farmer {i}",
            'type': 'farmer',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Milk',
            'supply': random.randint(500, 5000),
            'network_id': network_id
        })
        
    # 200 Hubs
    for i in range(1, 201):
        lat = round(random.uniform(21.5, 23.5), 4)
        lng = round(random.uniform(71.0, 73.5), 4)
        subtype = random.choice(['BMC', 'MCC', 'VLCC'])
        # Cow Milk
        rows.append({
            'node_id': f"H{i}",
            'name': f"Hub {i}",
            'type': 'hub',
            'subtype': subtype,
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Milk',
            'capacity': random.randint(8000, 20000),
            'cost': round(random.uniform(0.10, 0.25), 2),
            'network_id': network_id
        })
        # Buffalo Milk
        rows.append({
            'node_id': f"H{i}",
            'name': f"Hub {i}",
            'type': 'hub',
            'subtype': subtype,
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Milk',
            'capacity': random.randint(5000, 15000),
            'cost': round(random.uniform(0.15, 0.30), 2),
            'network_id': network_id
        })
        
    # 100 Plants
    for i in range(1, 101):
        lat = round(random.uniform(21.5, 23.5), 4)
        lng = round(random.uniform(71.0, 73.5), 4)
        
        # Raw cow milk capacity
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Milk',
            'capacity': random.randint(15000, 40000),
            'cost': round(random.uniform(0.30, 0.50), 2),
            'network_id': network_id
        })
        # Raw buffalo milk capacity
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Milk',
            'capacity': random.randint(10000, 30000),
            'cost': round(random.uniform(0.40, 0.60), 2),
            'network_id': network_id
        })
        # Cow Cheese yield
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Cheese',
            'yield': 0.10,
            'network_id': network_id
        })
        # Cow Liquid Milk yield
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Liquid Milk',
            'yield': 1.0,
            'network_id': network_id
        })
        # Buffalo Cheese yield
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Cheese',
            'yield': 0.10,
            'network_id': network_id
        })
        # Cow Khoya yield
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Khoya',
            'yield': 0.20,
            'network_id': network_id
        })
        # Buffalo Butter yield
        rows.append({
            'node_id': f"P{i}",
            'name': f"Plant {i}",
            'type': 'plant',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Butter',
            'yield': 0.06,
            'network_id': network_id
        })
        
    # 400 Geographies
    for i in range(1, 401):
        lat = round(random.uniform(21.5, 23.5), 4)
        lng = round(random.uniform(71.0, 73.5), 4)
        # Cow Liquid Milk demand/price
        rows.append({
            'node_id': f"G{i}",
            'name': f"Market {i}",
            'type': 'geography',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Liquid Milk',
            'demand': random.randint(1000, 5000),
            'price': round(random.uniform(55.0, 65.0), 1),
            'network_id': network_id
        })
        # Buffalo Cheese demand/price
        rows.append({
            'node_id': f"G{i}",
            'name': f"Market {i}",
            'type': 'geography',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Cheese',
            'demand': random.randint(50, 300),
            'price': round(random.uniform(700.0, 800.0), 1),
            'network_id': network_id
        })
        # Cow Khoya demand/price
        rows.append({
            'node_id': f"G{i}",
            'name': f"Market {i}",
            'type': 'geography',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Cow Khoya',
            'demand': random.randint(50, 200),
            'price': round(random.uniform(350.0, 450.0), 1),
            'network_id': network_id
        })
        # Buffalo Butter demand/price
        rows.append({
            'node_id': f"G{i}",
            'name': f"Market {i}",
            'type': 'geography',
            'subtype': '',
            'lat': lat,
            'lng': lng,
            'commodity': 'Buffalo Butter',
            'demand': random.randint(20, 100),
            'price': round(random.uniform(520.0, 620.0), 1),
            'network_id': network_id
        })
        
    df = pd.DataFrame(rows)
    all_cols = [
        'node_id', 'name', 'type', 'subtype', 'lat', 'lng', 
        'commodity', 'supply', 'capacity', 'cost', 'yield', 'demand', 'price', 
        'network_id'
    ]
    df = df.reindex(columns=all_cols)
    return df


def parse_excel_nodes(file_path_or_df):
    if isinstance(file_path_or_df, pd.DataFrame):
        df = file_path_or_df
    else:
        df = pd.read_excel(file_path_or_df)
    
    nodes = []
    
    # Clean string helper
    def clean_str(val, default=''):
        if pd.isna(val):
            return default
        return str(val).strip()
        
    # Clean float helper
    def clean_float(val, default=0.0):
        if pd.isna(val):
            return default
        try:
            return float(val)
        except ValueError:
            return default

    # Group by node_id preserving order of appearance
    grouped = df.groupby('node_id', sort=False)
    
    for node_id, group in grouped:
        if pd.isna(node_id) or not str(node_id).strip():
            continue
        
        node_id = str(node_id).strip()
        first_row = group.iloc[0]
        
        node_type = clean_str(first_row.get('type')).lower()
        
        # Resolve latitude and longitude columns dynamically and case-insensitively
        raw_lat = None
        raw_lng = None
        for col in first_row.index:
            col_lower = str(col).lower().strip()
            if col_lower in ('lat', 'latitude'):
                raw_lat = first_row[col]
            elif col_lower in ('lng', 'long', 'longitude'):
                raw_lng = first_row[col]
                
        node = {
            'id': node_id,
            'name': clean_str(first_row.get('name'), node_id),
            'type': node_type,
            'subtype': clean_str(first_row.get('subtype')),
            'lat': clean_float(raw_lat) if raw_lat is not None else clean_float(first_row.get('lat')),
            'lng': clean_float(raw_lng) if raw_lng is not None else clean_float(first_row.get('lng')),
            'network_id': clean_str(first_row.get('network_id'))
        }
        
        if node_type == 'farmer':
            supply_dict = {}
            for _, row in group.iterrows():
                commodity = clean_str(row.get('commodity'))
                supply = clean_float(row.get('supply'))
                if commodity and supply > 0:
                    supply_dict[commodity] = supply_dict.get(commodity, 0.0) + supply
            node['products'] = [{'type': k, 'supply': v} for k, v in supply_dict.items()]
            
        elif node_type == 'hub':
            products_dict = {}
            for _, row in group.iterrows():
                commodity = clean_str(row.get('commodity'))
                capacity = clean_float(row.get('capacity'))
                cost = clean_float(row.get('cost'))
                if commodity and capacity > 0:
                    if commodity not in products_dict:
                        products_dict[commodity] = {'capacity': 0.0, 'processing_cost': cost}
                    products_dict[commodity]['capacity'] += capacity
                    products_dict[commodity]['processing_cost'] = cost
            node['products'] = [{
                'type': k,
                'capacity': v['capacity'],
                'processing_cost': v['processing_cost']
            } for k, v in products_dict.items()]
            
        elif node_type == 'plant':
            inflow_dict = {}
            yield_dict = {}
            demand_dict = {}
            for _, row in group.iterrows():
                commodity = clean_str(row.get('commodity'))
                capacity = clean_float(row.get('capacity'))
                cost = clean_float(row.get('cost'))
                yield_val = clean_float(row.get('yield'))
                demand = clean_float(row.get('demand'))
                price = clean_float(row.get('price'))
                
                if capacity > 0 and commodity:
                    if commodity not in inflow_dict:
                        inflow_dict[commodity] = {'capacity': 0.0, 'processing_cost': cost}
                    inflow_dict[commodity]['capacity'] += capacity
                    inflow_dict[commodity]['processing_cost'] = cost
                if yield_val > 0 and commodity:
                    yield_dict[commodity] = yield_dict.get(commodity, 0.0) + yield_val
                if demand > 0 and commodity:
                    if commodity not in demand_dict:
                        demand_dict[commodity] = {'demand': 0.0, 'price': price, 'processing_cost': cost}
                    demand_dict[commodity]['demand'] += demand
                    demand_dict[commodity]['price'] = price
                    demand_dict[commodity]['processing_cost'] = cost
            
            node['inflow_milks'] = [{
                'type': k,
                'capacity': v['capacity'],
                'processing_cost': v['processing_cost']
            } for k, v in inflow_dict.items()]
            node['products'] = [{'type': k, 'yield': v} for k, v in yield_dict.items()]
            node['demands'] = [{
                'type': k,
                'demand': v['demand'],
                'price': v['price'],
                'processing_cost': v['processing_cost']
            } for k, v in demand_dict.items()]
            node['capacity'] = sum(m['capacity'] for m in node['inflow_milks']) if node['inflow_milks'] else sum(d['demand'] for d in node['demands'])
            node['processing_cost'] = node['inflow_milks'][0]['processing_cost'] if node['inflow_milks'] else (node['demands'][0]['processing_cost'] if node['demands'] else 0.40)
            
        elif node_type == 'geography':
            demand_dict = {}
            for _, row in group.iterrows():
                commodity = clean_str(row.get('commodity'))
                demand = clean_float(row.get('demand'))
                price = clean_float(row.get('price'))
                if commodity and demand > 0:
                    if commodity not in demand_dict:
                        demand_dict[commodity] = {'demand': 0.0, 'price': price}
                    demand_dict[commodity]['demand'] += demand
                    demand_dict[commodity]['price'] = price
            node['products'] = [{
                'type': k,
                'demand': v['demand'],
                'price': v['price']
            } for k, v in demand_dict.items()]
            
        nodes.append(node)
    return nodes


# Jobs DB Helpers supporting MongoDB / in-memory fallback
def get_all_jobs():
    if db_available:
        try:
            return list(db['jobs'].find({}).sort('created_at', -1))
        except Exception as e:
            print("Error listing jobs from MongoDB:", e)
    return sorted(in_memory_jobs, key=lambda x: x.get('created_at', ''), reverse=True)

def save_new_job(job):
    if db_available:
        try:
            db['jobs'].insert_one(job)
            return
        except Exception as e:
            print("Error inserting job to MongoDB:", e)
    in_memory_jobs.append(job)

def update_job_status(job_id, status):
    if db_available:
        try:
            db['jobs'].update_one({'job_id': job_id}, {'$set': {'status': status}})
            return
        except Exception as e:
            print("Error updating status in MongoDB:", e)
    for j in in_memory_jobs:
        if j['job_id'] == job_id:
            j['status'] = status
            break

def update_job_completed(job_id, output_filename, summary):
    completed_at = datetime.datetime.now().isoformat()
    if db_available:
        try:
            db['jobs'].update_one(
                {'job_id': job_id}, 
                {'$set': {
                    'status': 'COMPLETED', 
                    'output_filename': output_filename, 
                    'result_summary': summary,
                    'completed_at': completed_at
                }}
            )
            return
        except Exception as e:
            print("Error updating job completed in MongoDB:", e)
    for j in in_memory_jobs:
        if j['job_id'] == job_id:
            j['status'] = 'COMPLETED'
            j['output_filename'] = output_filename
            j['result_summary'] = summary
            j['completed_at'] = completed_at
            break

def update_job_failed(job_id, error_message):
    completed_at = datetime.datetime.now().isoformat()
    if db_available:
        try:
            db['jobs'].update_one(
                {'job_id': job_id}, 
                {'$set': {
                    'status': 'FAILED', 
                    'error_message': error_message,
                    'completed_at': completed_at
                }}
            )
            return
        except Exception as e:
            print("Error updating job failed in MongoDB:", e)
    for j in in_memory_jobs:
        if j['job_id'] == job_id:
            j['status'] = 'FAILED'
            j['error_message'] = error_message
            j['completed_at'] = completed_at
            break


# Yield factor per dairy product type
def get_yield_factor(product_type):
    ptype = (product_type or '').strip().lower()
    if 'cheese' in ptype:
        return 0.10      # 10 L milk = 1 kg cheese
    elif 'khoya' in ptype:
        return 0.20      # 5 L milk = 1 kg khoya
    elif 'butter' in ptype:
        return 0.06      # 16.7 L milk = 1 kg butter
    elif 'milk powder' in ptype:
        return 0.12      # 8.3 L milk = 1 kg milk powder
    return 1.0           # Liquid Milk or fallback

# Helper to determine raw milk type from finished product type
def get_milk_type_for_product(product_type):
    ptype = (product_type or '').strip()
    if ptype.endswith(' Cheese'):
        return ptype[:-7] + ' Milk'
    ptype_lower = ptype.lower()
    if 'buffalo' in ptype_lower:
        return 'Buffalo Milk'
    return 'Cow Milk'

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Helper to serialize MongoDB object
def serialize_node(node):
    node_dict = dict(node)
    if '_id' in node_dict:
        node_dict['_id'] = str(node_dict['_id'])
    return node_dict

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    # Only return interactive nodes (no network_id or empty network_id) to prevent map performance bottlenecks
    query = {'$or': [{'network_id': {'$exists': False}}, {'network_id': ''}, {'network_id': None}]}
    if db_available:
        try:
            db_nodes = list(nodes_collection.find(query))
            return jsonify([serialize_node(n) for n in db_nodes])
        except Exception as e:
            print(f"Error fetching from MongoDB: {e}")
    interactive_nodes = [n for n in in_memory_nodes if not n.get('network_id')]
    return jsonify(interactive_nodes)

@app.route('/api/nodes', methods=['POST'])
def add_node():
    new_node = request.json
    if not new_node or 'id' not in new_node:
        return jsonify({'status': 'ERROR', 'message': 'Invalid node data'}), 400
        
    # Remove _id to prevent modification of the immutable _id field in MongoDB
    new_node.pop('_id', None)

    if db_available:
        try:
            if nodes_collection.count_documents({'id': new_node['id']}) > 0:
                nodes_collection.replace_one({'id': new_node['id']}, new_node)
            else:
                nodes_collection.insert_one(new_node)
            saved_node = nodes_collection.find_one({'id': new_node['id']})
            return jsonify(serialize_node(saved_node)), 201
        except Exception as e:
            print(f"Error inserting into MongoDB: {e}")
            
    existing_idx = next((i for i, n in enumerate(in_memory_nodes) if n['id'] == new_node['id']), None)
    if existing_idx is not None:
        in_memory_nodes[existing_idx] = new_node
    else:
        in_memory_nodes.append(new_node)
    return jsonify(new_node), 201

@app.route('/api/nodes/<node_id>', methods=['PUT'])
def update_node(node_id):
    updated_data = request.json
    if not updated_data:
        return jsonify({'status': 'ERROR', 'message': 'No data provided'}), 400
        
    updated_data['id'] = node_id
    
    # Remove _id to prevent modification of the immutable _id field in MongoDB
    updated_data.pop('_id', None)

    if db_available:
        try:
            nodes_collection.replace_one({'id': node_id}, updated_data, upsert=True)
            saved_node = nodes_collection.find_one({'id': node_id})
            return jsonify(serialize_node(saved_node))
        except Exception as e:
            print(f"Error updating MongoDB: {e}")

    existing_idx = next((i for i, n in enumerate(in_memory_nodes) if n['id'] == node_id), None)
    if existing_idx is not None:
        in_memory_nodes[existing_idx] = updated_data
    else:
        in_memory_nodes.append(updated_data)
    return jsonify(updated_data)

@app.route('/api/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    if db_available:
        try:
            nodes_collection.delete_one({'id': node_id})
            return jsonify({'status': 'SUCCESS'})
        except Exception as e:
            print(f"Error deleting from MongoDB: {e}")

    global in_memory_nodes
    in_memory_nodes = [n for n in in_memory_nodes if n['id'] != node_id]
    return jsonify({'status': 'SUCCESS'})

@app.route('/api/nodes/reset', methods=['POST'])
def reset_nodes():
    # Only reset/delete interactive nodes, keeping the bulk jobs database nodes intact
    query = {'$or': [{'network_id': {'$exists': False}}, {'network_id': ''}, {'network_id': None}]}
    if db_available:
        try:
            nodes_collection.delete_many(query)
            nodes_collection.insert_many(DEFAULT_NODES)
            db_nodes = list(nodes_collection.find(query))
            return jsonify([serialize_node(n) for n in db_nodes])
        except Exception as e:
            print(f"Error resetting MongoDB: {e}")

    global in_memory_nodes
    in_memory_nodes = [n for n in in_memory_nodes if n.get('network_id')]
    in_memory_nodes.extend(DEFAULT_NODES)
    return jsonify(list(DEFAULT_NODES))


def get_optimal_vehicles(flow, vehicle_limits, caps=None, **kwargs):
    if caps is None:
        caps = {'7 L': 7000.0, '10 L': 10000.0, '12L': 12000.0, '15 L': 15000.0, '18 L': 18000.0}
    if isinstance(vehicle_limits, dict) and 'limits' in vehicle_limits:
        vehicle_limits = vehicle_limits['limits']

    if flow <= 0:
        return {}
        
    sorted_caps = sorted(caps.items(), key=lambda x: x[1], reverse=True)
        
    # fallback greedy
    def get_fallback():
        res = {k: 0 for k in caps.keys()}
        rem = flow
        for cap_name, cap_val in sorted_caps:
            limit = int(vehicle_limits.get(cap_name, 1000000))
            if limit <= 0:
                continue
            import math
            needed = int(math.ceil(rem / cap_val))
            taken = min(needed, limit)
            res[cap_name] = taken
            rem -= taken * cap_val
            if rem <= 0:
                break
        return {k: v for k, v in res.items() if v > 0}

    try:
        from ortools.linear_solver import pywraplp
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            return get_fallback()
            
        vars_dict = {}
        for name, cap in caps.items():
            limit = int(vehicle_limits.get(name, 1000000))
            vars_dict[name] = solver.IntVar(0, limit, f"count_{name}")
            
        solver.Add(sum(vars_dict[name] * cap for name, cap in caps.items()) >= flow)
        solver.Minimize(
            100000.0 * sum(vars_dict[name] for name in caps) +
            1.0 * sum(vars_dict[name] * cap for name, cap in caps.items())
        )
        
        status = solver.Solve()
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            result = {}
            for name in caps:
                val = int(round(vars_dict[name].solution_value()))
                if val > 0:
                    result[name] = val
            return result
        return get_fallback()
    except Exception:
        return get_fallback()


def get_vehicles_round_down(flow, vehicle_limits, caps=None):
    if caps is None:
        caps = {'7 L': 7000.0, '10 L': 10000.0, '12L': 12000.0, '15 L': 15000.0, '18 L': 18000.0}
    if isinstance(vehicle_limits, dict) and 'limits' in vehicle_limits:
        vehicle_limits = vehicle_limits['limits']

    sorted_caps = sorted(caps.items(), key=lambda x: x[1], reverse=True)

    def greedy_fallback():
        result = {k: 0 for k in caps}
        remaining = flow
        for cap_name, cap_val in sorted_caps:
            limit = int(vehicle_limits.get(cap_name, 1000000))
            if limit <= 0 or cap_val > remaining:
                continue
            taken = min(int(remaining // cap_val), limit)
            result[cap_name] = taken
            remaining -= taken * cap_val
        return {k: v for k, v in result.items() if v > 0}

    try:
        from ortools.linear_solver import pywraplp
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            return greedy_fallback()

        vars_dict = {}
        for name, cap in caps.items():
            limit = int(vehicle_limits.get(name, 1000000))
            vars_dict[name] = solver.IntVar(0, limit, f"rd_{name}")

        total_cap_expr = sum(vars_dict[n] * c for n, c in caps.items())
        solver.Add(total_cap_expr <= flow)
        solver.Maximize(total_cap_expr)
        
        status = solver.Solve()
        if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            result = {}
            for name in caps:
                val = int(round(vars_dict[name].solution_value()))
                if val > 0:
                    result[name] = val
            return result
        return greedy_fallback()
    except Exception:
        return greedy_fallback()


def parse_plant_bmc_mapping(excel_file_path):
    mapping = set()
    if not excel_file_path or not os.path.exists(excel_file_path):
        return mapping
    try:
        df = pd.read_excel(excel_file_path, sheet_name='Plant_BMC_Mapping')
        for _, row in df.iterrows():
            p_code = str(row.get('PlantCode', '')).strip()
            bmc_code = str(row.get('BMCCode', '')).strip()
            commodity = str(row.get('commodity', '')).strip()
            if p_code and bmc_code and commodity:
                mapping.add((p_code, bmc_code, commodity))
    except Exception as e:
        print(f"Error parsing Plant_BMC_Mapping (may not exist): {e}")
    return mapping

def parse_bmc_vehicles(excel_file_path):
    vehicle_limits_map = {}
    if not excel_file_path or not os.path.exists(excel_file_path):
        vehicle_limits_map['global_caps'] = {'7 L': 7000.0, '10 L': 10000.0, '12L': 12000.0, '15 L': 15000.0, '18 L': 18000.0}
        return vehicle_limits_map
        
    try:
        xl = pd.ExcelFile(excel_file_path)
        
        # 1. Parse Vehicle Type to get dynamic capacities
        caps = {}
        if 'Vehicle Type' in xl.sheet_names:
            df_vt = xl.parse('Vehicle Type')
            capacity_col = next((c for c in df_vt.columns if 'name' in str(c).lower() or 'capacity' in str(c).lower() or 'type' in str(c).lower()), None)
            code_col = next((c for c in df_vt.columns if 'code' in str(c).lower() or 'vehiclecode' in str(c).lower()), 'VehicleCode')
            to_col = next((c for c in df_vt.columns if str(c).lower() == 'to'), 'To')
            
            if code_col in df_vt.columns and to_col in df_vt.columns:
                for _, row in df_vt.iterrows():
                    vc = str(row[code_col]).strip()
                    to_val = float(row[to_col]) if pd.notnull(row[to_col]) else 0.0
                    caps[vc] = to_val * 1000.0
        
        # Fallback
        if not caps:
            caps = {'7 L': 7000.0, '10 L': 10000.0, '12L': 12000.0, '15 L': 15000.0, '18 L': 18000.0}
            
        vehicle_limits_map['global_caps'] = caps

        sheet_name = None
        for s in xl.sheet_names:
            if s.lower().replace(' ', '').replace('_', '') == 'vehiclesupplierallocation':
                sheet_name = s
                break
        if not sheet_name:
            for s in xl.sheet_names:
                if 'supplier' in s.lower() and 'allocation' in s.lower():
                    sheet_name = s
                    break
        if sheet_name:
            df_veh = xl.parse(sheet_name)
            # Find ID column
            id_col = next((c for c in df_veh.columns if str(c).lower().replace(' ', '').replace('_', '') == 'suppliercluster'), None)
            if not id_col and len(df_veh.columns) > 0:
                id_col = df_veh.columns[0]
                
            if id_col:
                col_strat = next((c for c in df_veh.columns if 'strategy' in str(c).lower().replace(' ', '').replace('_', '')), None)
                col_margin_low = next((c for c in df_veh.columns if 'flowlowmargin' in str(c).lower().replace(' ', '').replace('_', '')), None)
                col_margin_high = next((c for c in df_veh.columns if 'flowhighmargin' in str(c).lower().replace(' ', '').replace('_', '')), None)
                col_cluster = next((c for c in df_veh.columns if 'cluster' in str(c).lower() and 'sub' not in str(c).lower()), None)
                col_subcluster = next((c for c in df_veh.columns if 'subcluster' in str(c).lower().replace(' ', '').replace('_', '')), None)
                
                vehicle_cols = {}
                for vc in caps.keys():
                    vc_norm = str(vc).lower().replace(' ', '').strip()
                    for c in df_veh.columns:
                        if str(c).lower().replace(' ', '').strip() == vc_norm:
                            vehicle_cols[vc] = c
                            break
                            
                for _, row in df_veh.iterrows():
                    bmc_id = str(row[id_col]).strip()
                    if bmc_id and bmc_id.lower() != 'nan':
                        limits = {}
                        for vc in caps.keys():
                            c_name = vehicle_cols.get(vc)
                            limits[vc] = float(row[c_name]) if (c_name and pd.notna(row[c_name])) else 1000000.0
                            
                        strategy = str(row[col_strat]).strip() if col_strat and pd.notna(row[col_strat]) else "Whole Milk Supply"
                        margin_low = float(row[col_margin_low]) if col_margin_low and pd.notna(row[col_margin_low]) else 5.0
                        margin_high = float(row[col_margin_high]) if col_margin_high and pd.notna(row[col_margin_high]) else 5.0
                        cluster = str(row[col_cluster]).strip() if col_cluster and pd.notna(row[col_cluster]) else ""
                        subcluster = str(row[col_subcluster]).strip() if col_subcluster and pd.notna(row[col_subcluster]) else ""
                        
                        vehicle_limits_map[bmc_id] = {
                            'limits': limits,
                            'strategy': strategy,
                            'margin_low': margin_low,
                            'margin_high': margin_high,
                            'cluster': cluster,
                            'subcluster': subcluster
                        }
            print(f"Loaded vehicle limits for {len(vehicle_limits_map)-1} Suppliers from Excel")
    except Exception as e:
        print("Error parsing BMCVechicle sheet:", e)
        
    return vehicle_limits_map


def solve_network_lp(farmers, hubs, plants, geographies, transport_cost_per_km=0.005, excel_file_path=None):
    plant_bmc_mapping = parse_plant_bmc_mapping(excel_file_path)
    try:
        from ortools.linear_solver import pywraplp
    except ImportError:
        return {
            'status': 'ERROR',
            'message': 'Google OR-Tools is not installed or available in the environment.'
        }

    # Load BMC vehicle limits from uploaded Excel file if it exists
    vehicle_limits_map = parse_bmc_vehicles(excel_file_path)
    
    # Create BMC to Supplier Mapping for quick lookup
    bmc_to_supplier = {}
    try:
        if excel_file_path and os.path.exists(excel_file_path):
            df_map = pd.read_excel(excel_file_path, sheet_name='Plant_BMC_Mapping')
            if 'Supplier' in df_map.columns:
                bmc_to_supplier = df_map.drop_duplicates(subset=['BMCCode']).set_index('BMCCode')['Supplier'].to_dict()
    except:
        pass

    # Initialize solver
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return {'status': 'ERROR', 'message': 'Could not create GLOP solver.'}

    # Pre-calculate candidate distances using OSRM Table API
    total_nodes_count = len(hubs) + len(plants) + len(geographies)
    is_large = total_nodes_count > 50
    dist_cache = {}
    
    # Load precalculated distances from Distance sheet in Excel if present
    if excel_file_path and os.path.exists(excel_file_path):
        try:
            xl = pd.ExcelFile(excel_file_path)
            distance_sheet_name = None
            for s in xl.sheet_names:
                if s.lower().strip() == 'distance':
                    distance_sheet_name = s
                    break
            if distance_sheet_name:
                df_dist = xl.parse(distance_sheet_name)
                col_hub = next((c for c in df_dist.columns if any(k in str(c).lower() for k in ['hub', 'bmc', 'mcc', 'source', 'from'])), None)
                col_plant = next((c for c in df_dist.columns if any(k in str(c).lower() for k in ['plant', 'to', 'dest', 'target'])), None)
                col_dist = next((c for c in df_dist.columns if any(k in str(c).lower() for k in ['dist', 'km'])), None)
                
                if col_hub and col_plant and col_dist:
                    def canonicalize_id(val):
                        if pd.isna(val) or val is None:
                            return ""
                        return "".join(c for c in str(val).lower() if c.isalnum())
                    
                    hub_id_map = {}
                    for h in hubs:
                        hub_id_map[canonicalize_id(h['id'])] = h['id']
                        hub_id_map[canonicalize_id(h.get('name'))] = h['id']
                        
                    plant_id_map = {}
                    for p in plants:
                        plant_id_map[canonicalize_id(p['id'])] = p['id']
                        plant_id_map[canonicalize_id(p.get('name'))] = p['id']
                        
                    loaded_count = 0
                    for _, row in df_dist.iterrows():
                        h_raw = canonicalize_id(row[col_hub])
                        p_raw = canonicalize_id(row[col_plant])
                        d_val = row[col_dist]
                        
                        h_id = hub_id_map.get(h_raw)
                        p_id = plant_id_map.get(p_raw)
                        
                        if h_id and p_id and pd.notna(d_val):
                            dist_cache[(h_id, p_id)] = float(d_val)
                            pair_key = tuple(sorted([h_id, p_id]))
                            _distance_cache[pair_key] = float(d_val)
                            loaded_count += 1
                            
                    print(f"Loaded {loaded_count} precalculated distances from Excel sheet 'Distance'")
        except Exception as e:
            print("Error loading distances from Excel sheet 'Distance':", e)

    # 1. Hub -> Plant
    for h in hubs:
        for p in plants:
            if (h['id'], p['id']) not in dist_cache:
                dist_cache[(h['id'], p['id'])] = calculate_haversine_distance(h, p)
                
    # 2. Plant -> Geography
    for g in geographies:
        for p in plants:
            if (p['id'], g['id']) not in dist_cache:
                dist_cache[(p['id'], g['id'])] = calculate_haversine_distance(p, g)

    # Helper to resolve distance
    def get_pair_dist(node1, node2):
        key = (node1['id'], node2['id'])
        if key in dist_cache:
            return dist_cache[key]
        if is_large:
            return calculate_haversine_distance(node1, node2)
        return get_road_distance(node1, node2)

    # Dynamically extract all raw milk types present in hubs
    milk_types = set()
    for h in hubs:
        h_prods = h.get('products', [])
        if not h_prods and 'capacity' in h:
            h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity'], 'processing_cost': h.get('processing_cost', 0)}]
        for p in h_prods:
            if 'type' in p:
                milk_types.add(p['type'])
    if not milk_types:
        milk_types = {'Cow Milk', 'Buffalo Milk'}
    milk_types = sorted(list(milk_types))

    # Decision Variables
    # Flow: Hub -> Plant per Milk Type
    flow_h_p = {}
    for h in hubs:
        h_prods = h.get('products', [])
        if not h_prods and 'capacity' in h:
            h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity']}]
        h_types = {p['type'] for p in h_prods if 'type' in p}
        for p in plants:
            if is_large and (h['id'], p['id']) not in dist_cache:
                continue
            
            p_demands = p.get('demands', [])
            p_demand_types = {d['type'] for d in p_demands if 'type' in d}
            
            p_products = p.get('products', [])
            if not p_products and 'production_type' in p:
                p_products = [{'type': p['production_type'], 'yield': get_yield_factor(p['production_type'])}]
            p_milk_types = {get_milk_type_for_product(prod['type']) for prod in p_products if 'type' in prod}
            
            common_milk = h_types.intersection(p_milk_types.union(p_demand_types))
            if common_milk:
                dist = get_pair_dist(h, p)
                if dist <= MAX_DISTANCE_LIMIT:
                    for m in common_milk:
                        # Strict mapping logic: if mapping exists, only allow mapped routes
                        if plant_bmc_mapping and (str(p['id']), str(h['id']), str(m)) not in plant_bmc_mapping:
                            continue
                            
                        clean_m = m.replace(' ', '_').replace('-', '_')
                        name = f"flow_H_{h['id']}_P_{p['id']}_{clean_m}"
                        flow_h_p[(h['id'], p['id'], m)] = solver.NumVar(0, solver.infinity(), name)

    # Flow: Plant -> Geography (flow is in physical units of product, e.g., kg/L, per product)
    flow_p_g = {}
    for p in plants:
        p_products = p.get('products', [])
        if not p_products and 'production_type' in p:
            p_products = [{'type': p['production_type'], 'yield': get_yield_factor(p['production_type'])}]
            
        for g in geographies:
            if is_large and (p['id'], g['id']) not in dist_cache:
                continue
            g_products = g.get('products', [])
            if not g_products and 'product_type' in g:
                g_products = [{'type': g['product_type'], 'demand': g.get('demand', 0), 'price': g.get('price', 0)}]
                
            common_types = set(prod['type'] for prod in p_products if 'type' in prod).intersection(set(prod['type'] for prod in g_products if 'type' in prod))
            if common_types:
                dist = get_pair_dist(p, g)
                if dist <= MAX_DISTANCE_LIMIT:
                    for ptype in common_types:
                        clean_ptype = ptype.replace(' ', '_').replace('-', '_')
                        name = f"flow_P_{p['id']}_G_{g['id']}_{clean_ptype}"
                        flow_p_g[(p['id'], g['id'], ptype)] = solver.NumVar(0, solver.infinity(), name)

    # Precompute nearest plant map for each hub and milk type
    nearest_plant_map = {}
    for h in hubs:
        for m in milk_types:
            compatible_plants = [p for p in plants if (h['id'], p['id'], m) in flow_h_p]
            if compatible_plants:
                p_near = min(compatible_plants, key=lambda p: get_pair_dist(h, p))
                nearest_plant_map[(h['id'], m)] = p_near['id']

    # Required vs Excess Flow Variables for Hub -> Plant
    flow_required = {}
    flow_excess = {}
    for (h_id, p_id, m), flow_var in flow_h_p.items():
        clean_m = m.replace(' ', '_').replace('-', '_')
        flow_required[(h_id, p_id, m)] = solver.NumVar(0, solver.infinity(), f"flow_req_H_{h_id}_P_{p_id}_{clean_m}")
        flow_excess[(h_id, p_id, m)] = solver.NumVar(0, solver.infinity(), f"flow_exc_H_{h_id}_P_{p_id}_{clean_m}")
        solver.Add(flow_var == flow_required[(h_id, p_id, m)] + flow_excess[(h_id, p_id, m)])
        
        # If this plant is not the nearest plant for this hub/milk, excess flow must be 0
        p_near_id = nearest_plant_map.get((h_id, m))
        if p_near_id and p_id != p_near_id:
            solver.Add(flow_excess[(h_id, p_id, m)] == 0)

    # Constraints
    slack_vars = []

    # Precompute plant inflows for the Even Distribution Rule (using required flow only)
    plant_inflow_vars = {}
    for p in plants:
        for m in milk_types:
            plant_inflow_vars[(p['id'], m)] = [
                flow_required[(h_other['id'], p['id'], m)]
                for h_other in hubs
                if (h_other['id'], p['id'], m) in flow_h_p
            ]

    # 1. Hub supply limits (per milk type)
    for h in hubs:
        h_prods = h.get('products', [])
        if not h_prods and 'capacity' in h:
            h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity'], 'processing_cost': h.get('processing_cost', 0)}]
        capacity_dict = {p['type']: p.get('capacity', 0) for p in h_prods if 'type' in p}
        
        for m in milk_types:
            flow_out_vars = [flow_h_p[(h['id'], p['id'], m)] for p in plants if (h['id'], p['id'], m) in flow_h_p]
            cap_limit = capacity_dict.get(m, 0)
            if cap_limit > 0:
                if flow_out_vars:
                    slack = solver.NumVar(0, solver.infinity(), f"slack_hub_{h['id']}_{m.replace(' ', '_')}")
                    solver.Add(sum(flow_out_vars) + slack == cap_limit)
                    slack_vars.append(slack * 10000000.0)
                    
                    # Even Distribution Rule (Equalize total plant inflows proportionally to plant demands)
                    eligible_plants = [p for p in plants if (h['id'], p['id'], m) in flow_h_p]
                    if len(eligible_plants) > 1:
                        clean_m = m.replace(' ', '_').replace('-', '_')
                        for i in range(len(eligible_plants) - 1):
                            p1 = eligible_plants[i]
                            p2 = eligible_plants[i + 1]
                            
                            # Resolve capacities or demands for plant 1
                            inflow_milks1 = p1.get('inflow_milks', [])
                            cap_dict1 = {x['type']: x.get('capacity', 0) for x in inflow_milks1 if 'type' in x}
                            cap1 = cap_dict1.get(m, 0)
                            if cap1 <= 0:
                                demands1 = p1.get('demands', []) or []
                                demands_dict1 = {x['type']: x.get('demand', 0) for x in demands1 if 'type' in x}
                                cap1 = demands_dict1.get(m, 0)
                            if cap1 <= 0:
                                cap1 = p1.get('capacity', 0)
                            if cap1 <= 0:
                                cap1 = 1.0
                                
                            # Resolve capacities or demands for plant 2
                            inflow_milks2 = p2.get('inflow_milks', [])
                            cap_dict2 = {x['type']: x.get('capacity', 0) for x in inflow_milks2 if 'type' in x}
                            cap2 = cap_dict2.get(m, 0)
                            if cap2 <= 0:
                                demands2 = p2.get('demands', []) or []
                                demands_dict2 = {x['type']: x.get('demand', 0) for x in demands2 if 'type' in x}
                                cap2 = demands_dict2.get(m, 0)
                            if cap2 <= 0:
                                cap2 = p2.get('capacity', 0)
                            if cap2 <= 0:
                                cap2 = 1.0
                            
                            # Sum of all inflows to p1 and p2 for commodity m
                            total_inflow_p1 = sum(plant_inflow_vars.get((p1['id'], m), []))
                            total_inflow_p2 = sum(plant_inflow_vars.get((p2['id'], m), []))
                            
                            diff = solver.NumVar(0, solver.infinity(), f"diff_H_{h['id']}_P1_{p1['id']}_P2_{p2['id']}_{clean_m}")
                            solver.Add(total_inflow_p1 * (1.0 / cap1) - total_inflow_p2 * (1.0 / cap2) <= diff)
                            solver.Add(total_inflow_p2 * (1.0 / cap2) - total_inflow_p1 * (1.0 / cap1) <= diff)
                            slack_vars.append(diff * 100000.0)

            else:
                if flow_out_vars:
                    solver.Add(sum(flow_out_vars) == 0)

    # 2. Plant capacity & flow conservation (conservation per milk type, total capacity limit)
    for p in plants:
        p_products = p.get('products', [])
        if not p_products and 'production_type' in p:
            p_products = [{'type': p['production_type'], 'yield': get_yield_factor(p['production_type'])}]
        p_yields = {prod['type']: prod.get('yield', 1.0) for prod in p_products if 'type' in prod}
        
        p_demands = p.get('demands', [])
        demand_dict = {d['type']: d.get('demand', 0) for d in p_demands if 'type' in d}
        
        inflow_milks = p.get('inflow_milks', [])
        if not inflow_milks:
            if p_demands:
                inflow_milks = [{'type': d['type'], 'capacity': d['demand'], 'processing_cost': d.get('processing_cost', 0.40)} for d in p_demands]
            else:
                inflow_milks = [
                    {'type': 'Cow Milk', 'capacity': p.get('capacity', 10000), 'processing_cost': p.get('processing_cost', 0.50)},
                    {'type': 'Buffalo Milk', 'capacity': p.get('capacity', 10000), 'processing_cost': p.get('processing_cost', 0.50)}
                ]
        capacity_dict = {m['type']: m.get('capacity', 0) for m in inflow_milks if 'type' in m}
        
        # Substitution variables: BM -> FCM -> MM
        trans_BM_FCM = solver.NumVar(0, solver.infinity(), f"trans_{p['id']}_BM_to_FCM")
        trans_FCM_MM = solver.NumVar(0, solver.infinity(), f"trans_{p['id']}_FCM_to_MM")
        
        if 'trans_vars' not in locals():
            trans_vars = {}
        trans_vars[(p['id'], 'BM_to_FCM')] = trans_BM_FCM
        trans_vars[(p['id'], 'FCM_to_MM')] = trans_FCM_MM
        
        # Small penalty to prefer direct matches before downgrading
        slack_vars.append(trans_BM_FCM * 10.0)
        slack_vars.append(trans_FCM_MM * 10.0)
        
        for m in milk_types:
            flow_in_m = sum(flow_h_p[(h['id'], p['id'], m)] for h in hubs if (h['id'], p['id'], m) in flow_h_p)
            
            effective_flow_in = flow_in_m
            m_lower = str(m).lower()
            if 'buffalo' in m_lower or 'bm' in m_lower:
                effective_flow_in = flow_in_m - trans_BM_FCM
            elif 'fcm' in m_lower:
                effective_flow_in = flow_in_m + trans_BM_FCM - trans_FCM_MM
            elif 'mm' in m_lower:
                effective_flow_in = flow_in_m + trans_FCM_MM
            
            # Bound required flow into plant to its required supply limit (R_{p,m})
            r_limit = 0.0
            if m in demand_dict:
                r_limit = demand_dict[m]
            else:
                r_limit = capacity_dict.get(m, 0.0)
            
            req_inflow_vars = [
                flow_required[(h['id'], p['id'], m)]
                for h in hubs
                if (h['id'], p['id'], m) in flow_h_p
            ]
            if req_inflow_vars:
                solver.Add(sum(req_inflow_vars) <= r_limit)
            
            if m in demand_dict:
                # Soft plant demand capacity constraint (2-tier Excel mode)
                over_cap = solver.NumVar(0, solver.infinity(), f"over_cap_{p['id']}_{m.replace(' ', '_')}")
                solver.Add(effective_flow_in - over_cap <= demand_dict[m])
                slack_vars.append(over_cap * 1000000.0)
            else:
                outflow_milk_equivalent = []
                for g in geographies:
                    g_products = g.get('products', [])
                    if not g_products and 'product_type' in g:
                        g_products = [{'type': g['product_type'], 'demand': g.get('demand', 0), 'price': g.get('price', 0)}]
                    
                    common_types = set(p_yields.keys()).intersection(set(prod['type'] for prod in g_products if 'type' in prod))
                    for ptype in common_types:
                        if get_milk_type_for_product(ptype) == m:
                            yf = p_yields[ptype]
                            if yf <= 0:
                                yf = 1.0
                            if (p['id'], g['id'], ptype) in flow_p_g:
                                outflow_milk_equivalent.append(flow_p_g[(p['id'], g['id'], ptype)] * (1.0 / yf))
                
                solver.Add(effective_flow_in == sum(outflow_milk_equivalent))
                
                cap_limit = capacity_dict.get(m, 0)
                if cap_limit > 0:
                    # Soft capacity limit: effective_flow_in <= cap_limit + over_cap
                    over_cap = solver.NumVar(0, solver.infinity(), f"over_cap_{p['id']}_{m.replace(' ', '_')}")
                    solver.Add(effective_flow_in - over_cap <= cap_limit)
                    slack_vars.append(over_cap * 1000000.0)
                else:
                    solver.Add(effective_flow_in == 0)

        # Ensure plant is fulfilled at least 20 percent of its capacity
        total_capacity = sum(capacity_dict.values()) if capacity_dict else p.get('capacity', 0)
        if total_capacity > 0:
            inflow_vars = [flow_h_p[(h['id'], p['id'], m)] for h in hubs for m in milk_types if (h['id'], p['id'], m) in flow_h_p]
            if inflow_vars:
                plant_slack = solver.NumVar(0, solver.infinity(), f"slack_plant_{p['id']}")
                solver.Add(sum(inflow_vars) + plant_slack >= 0.20 * total_capacity)
                slack_vars.append(plant_slack * 10000000.0)

    # 3. Geography demand limit (in product units, per product)
    for g in geographies:
        g_products = g.get('products', [])
        if not g_products and 'product_type' in g:
            g_products = [{'type': g['product_type'], 'demand': g.get('demand', 0), 'price': g.get('price', 0)}]
        
        for g_prod in g_products:
            ptype = g_prod.get('type')
            if not ptype:
                continue
            demand_val = g_prod.get('demand', 0)
            
            flows_for_prod = []
            for p in plants:
                if (p['id'], g['id'], ptype) in flow_p_g:
                    flows_for_prod.append(flow_p_g[(p['id'], g['id'], ptype)])
            
            if flows_for_prod:
                over_geo = solver.NumVar(0, solver.infinity(), f"over_geo_{g['id']}_{ptype.replace(' ', '_')}")
                solver.Add(sum(flows_for_prod) - over_geo <= demand_val)
                slack_vars.append(over_geo * 1000000.0)

    # Objective: Maximize Profit
    # Profit = Revenue - Transport Cost - Processing/Handling Cost

    # 1. Revenue
    revenue_items = []
    for g in geographies:
        g_products = g.get('products', [])
        if not g_products and 'product_type' in g:
            g_products = [{'type': g['product_type'], 'demand': g.get('demand', 0), 'price': g.get('price', 0)}]
        g_prices = {prod['type']: prod.get('price', 0.0) for prod in g_products if 'type' in prod}
        
        for p in plants:
            for ptype, price in g_prices.items():
                if (p['id'], g['id'], ptype) in flow_p_g:
                    revenue_items.append(flow_p_g[(p['id'], g['id'], ptype)] * price)
                    
    for p in plants:
        p_demands = p.get('demands', [])
        for d in p_demands:
            m = d['type']
            price = d.get('price', 0.0)
            flow_in_m_vars = [flow_h_p[(h['id'], p['id'], m)] for h in hubs if (h['id'], p['id'], m) in flow_h_p]
            if flow_in_m_vars:
                revenue_items.append(sum(flow_in_m_vars) * price)
                
    revenue_expr = sum(revenue_items)

    # 2. Transport Costs
    trans_cost_expr = []
    # Hub -> Plant
    for (h_id, p_id, m), flow_var in flow_h_p.items():
        h_node = next(x for x in hubs if x['id'] == h_id)
        p_node = next(x for x in plants if x['id'] == p_id)
        dist = get_pair_dist(h_node, p_node)
        # Use actual distance to favor nearest plant
        effective_dist = dist
        cost_per_unit = effective_dist * transport_cost_per_km
        
        # Commodity Priority Logic: BM > FCM > MM
        m_lower = str(m).lower()
        bonus = 0.0
        if 'buffalo' in m_lower or 'bm' in m_lower:
            bonus = 0.003
        elif 'fcm' in m_lower:
            bonus = 0.002
        elif 'mm' in m_lower:
            bonus = 0.001
            
        cost_per_unit -= bonus
            
        trans_cost_expr.append(flow_var * cost_per_unit)
    # Plant -> Geography (Cost scales with actual finished product units shipped)
    for (p_id, g_id, ptype), flow_var in flow_p_g.items():
        p_node = next(x for x in plants if x['id'] == p_id)
        g_node = next(x for x in geographies if x['id'] == g_id)
        dist = get_pair_dist(p_node, g_node)
        # Use actual distance to favor nearest plant
        effective_dist = dist
        cost_per_unit = effective_dist * transport_cost_per_km
        trans_cost_expr.append(flow_var * cost_per_unit)

    # 3. Processing/Handling Costs at Hubs and Plants
    proc_cost_expr = []
    for h in hubs:
        h_prods = h.get('products', [])
        if not h_prods and 'capacity' in h:
            h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity'], 'processing_cost': h.get('processing_cost', 0)}]
        cost_dict = {p['type']: p.get('processing_cost', 0.0) for p in h_prods if 'type' in p}
        for m in milk_types:
            flow_out_m = sum(flow_h_p[(h['id'], p['id'], m)] for p in plants if (h['id'], p['id'], m) in flow_h_p)
            proc_cost_expr.append(flow_out_m * cost_dict.get(m, 0.0))
            
    for p in plants:
        inflow_milks = p.get('inflow_milks', [])
        if not inflow_milks:
            p_demands = p.get('demands', [])
            if p_demands:
                inflow_milks = [{'type': d['type'], 'capacity': d['demand'], 'processing_cost': d.get('processing_cost', 0.40)} for d in p_demands]
            else:
                inflow_milks = [
                    {'type': 'Cow Milk', 'capacity': p.get('capacity', 10000), 'processing_cost': p.get('processing_cost', 0.50)},
                    {'type': 'Buffalo Milk', 'capacity': p.get('capacity', 10000), 'processing_cost': p.get('processing_cost', 0.50)}
                ]
        cost_dict = {m['type']: m.get('processing_cost', 0.0) for m in inflow_milks if 'type' in m}
        for m in milk_types:
            flow_in_m = sum(flow_h_p[(h['id'], p['id'], m)] for h in hubs if (h['id'], p['id'], m) in flow_h_p)
            proc_cost_expr.append(flow_in_m * cost_dict.get(m, 0.40))

    solver.Maximize(revenue_expr - sum(trans_cost_expr) - sum(proc_cost_expr) - sum(slack_vars))

    status = solver.Solve()



    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        routes = []

        # Extract Hub -> Plant flows
        for (h_id, p_id, m), flow_var in flow_h_p.items():
            val = flow_var.solution_value()
            if val > 0.1:
                h_node = next(x for x in hubs if x['id'] == h_id)
                p_node = next(x for x in plants if x['id'] == p_id)
                dist = get_pair_dist(h_node, p_node)
                cost = dist * transport_cost_per_km * val
                clean_m = m.replace(' ', '_').replace('-', '_')
                
                # Calculate optimal vehicles
                supplier = bmc_to_supplier.get(h_id, '')
                limits = vehicle_limits_map.get(supplier, {})
                optimal_veh = get_optimal_vehicles(val, limits, caps=vehicle_limits_map.get('global_caps'))
                global_caps = vehicle_limits_map.get('global_caps', {})
                total_veh = sum(optimal_veh.values())
                total_cap = sum(count * global_caps.get(v, 0) for v, count in optimal_veh.items())
                excess = total_cap - val if total_veh > 0 else 0.0
                
                routes.append({
                    'id': f"route_{h_id}_{p_id}_{clean_m}",
                    'from_id': h_id,
                    'to_id': p_id,
                    'from_type': 'hub',
                    'to_type': 'plant',
                    'flow': round(val, 2),
                    'product_type': m,
                    'unit': 'L',
                    'distance': round(dist, 2),
                    'cost': round(cost, 2),
                    'total_vehicles': total_veh,
                    'total_vehicle_capacity': total_cap,
                    'excess_vehicle_capacity': round(excess, 2)
                })

        # Extract Plant -> Geography flows
        for (p_id, g_id, ptype), flow_var in flow_p_g.items():
            val = flow_var.solution_value()
            if val > 0.1:
                p_node = next(x for x in plants if x['id'] == p_id)
                g_node = next(x for x in geographies if x['id'] == g_id)
                dist = get_pair_dist(p_node, g_node)
                cost = dist * transport_cost_per_km * val
                unit = 'kg' if any(k in ptype.strip().lower() for k in ['cheese', 'khoya', 'butter', 'milk powder']) else 'L'
                routes.append({
                    'id': f"route_{p_id}_{g_id}_{ptype.replace(' ', '_')}",
                    'from_id': p_id,
                    'to_id': g_id,
                    'from_type': 'plant',
                    'to_type': 'geography',
                    'flow': round(val, 2),
                    'product_type': ptype,
                    'unit': unit,
                    'distance': round(dist, 2),
                    'cost': round(cost, 2)
                })

        # Aggregate metrics
        obj_val = solver.Objective().Value()
        
        total_revenue = sum(
            flow_var.solution_value() * next(
                (prod.get('price', 0.0) for prod in next(g for g in geographies if g['id'] == g_id).get('products', []) if prod.get('type') == ptype),
                next(g for g in geographies if g['id'] == g_id).get('price', 0.0)
            )
            for (p_id, g_id, ptype), flow_var in flow_p_g.items() if flow_var.solution_value() > 0.1
        )

        for p in plants:
            p_demands = p.get('demands', [])
            for d in p_demands:
                m = d['type']
                price = d.get('price', 0.0)
                flow_in_val = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for h in hubs if (h['id'], p['id'], m) in flow_h_p)
                if flow_in_val > 0.1:
                    total_revenue += flow_in_val * price

        total_transport_cost = sum(r['cost'] for r in routes)

        total_hub_proc_cost = 0.0
        for h in hubs:
            h_prods = h.get('products', [])
            if not h_prods and 'capacity' in h:
                h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity'], 'processing_cost': h.get('processing_cost', 0)}]
            cost_dict = {p['type']: p.get('processing_cost', 0.0) for p in h_prods if 'type' in p}
            for m in milk_types:
                flow_out_m = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for p in plants if (h['id'], p['id'], m) in flow_h_p)
                total_hub_proc_cost += flow_out_m * cost_dict.get(m, 0.0)

        total_plant_proc_cost = 0.0
        for p in plants:
            inflow_milks = p.get('inflow_milks', [])
            if not inflow_milks:
                p_demands = p.get('demands', [])
                if p_demands:
                    inflow_milks = [{'type': d['type'], 'capacity': d['demand'], 'processing_cost': d.get('processing_cost', 0.40)} for d in p_demands]
                else:
                    inflow_milks = [
                        {'type': 'Cow Milk', 'capacity': p.get('capacity', 10000), 'processing_cost': p.get('processing_cost', 0.50)},
                        {'type': 'Buffalo Milk', 'capacity': p.get('capacity', 10000), 'processing_cost': p.get('processing_cost', 0.50)}
                    ]
            cost_dict = {m['type']: m.get('processing_cost', 0.0) for m in inflow_milks if 'type' in m}
            for m in milk_types:
                flow_in_m = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for h in hubs if (h['id'], p['id'], m) in flow_h_p)
                total_plant_proc_cost += flow_in_m * cost_dict.get(m, 0.40)

        total_proc_cost = total_hub_proc_cost + total_plant_proc_cost

        # Flow summary per node
        node_metrics = {}
        for h in hubs:
            out_val = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for p in plants for m in milk_types if (h['id'], p['id'], m) in flow_h_p)
            node_metrics[h['id']] = {
                'inflow': 0.0,
                'outflow': round(out_val, 2)
            }
        for p in plants:
            in_val = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for h in hubs for m in milk_types if (h['id'], p['id'], m) in flow_h_p)
            
            p_demands = p.get('demands', [])
            if p_demands:
                outflow_milk = in_val
            else:
                outflow_milk = 0.0
                p_products = p.get('products', [])
                if not p_products and 'production_type' in p:
                    p_products = [{'type': p['production_type'], 'yield': get_yield_factor(p['production_type'])}]
                p_yields = {prod['type']: prod.get('yield', 1.0) for prod in p_products if 'type' in prod}
                
                for (p_id, g_id, ptype), flow_var in flow_p_g.items():
                    if p_id == p['id']:
                        yf = p_yields.get(ptype, 1.0)
                        if yf <= 0:
                            yf = 1.0
                        outflow_milk += flow_var.solution_value() / yf

            node_metrics[p['id']] = {
                'inflow': round(in_val, 2),
                'outflow': round(outflow_milk, 2)
            }
        for g in geographies:
            inflow_milk = 0.0
            for (p_id, g_id, ptype), flow_var in flow_p_g.items():
                if g_id == g['id']:
                    p_node = next(x for x in plants if x['id'] == p_id)
                    p_products = p_node.get('products', [])
                    if not p_products and 'production_type' in p_node:
                        p_products = [{'type': p_node['production_type'], 'yield': get_yield_factor(p_node['production_type'])}]
                    yf = next((prod.get('yield', 1.0) for prod in p_products if prod.get('type') == ptype), 1.0)
                    if yf <= 0:
                        yf = 1.0
                    inflow_milk += flow_var.solution_value() / yf

            node_metrics[g['id']] = {
                'inflow': round(inflow_milk, 2),
                'outflow': 0.0
            }

        return {
            'status': 'OPTIMAL',
            'summary': {
                'profit': round(obj_val, 2),
                'revenue': round(total_revenue, 2),
                'transport_cost': round(total_transport_cost, 2),
                'processing_cost': round(total_proc_cost, 2),
                'hub_processing_cost': round(total_hub_proc_cost, 2),
                'plant_processing_cost': round(total_plant_proc_cost, 2)
            },
            'routes': routes,
            'node_metrics': node_metrics,
            'trans_vars_solution': {k: v.solution_value() for k, v in trans_vars.items()} if 'trans_vars' in locals() else {}
        }
    else:
        return {
            'status': 'INFEASIBLE',
            'message': 'The model is infeasible or unbounded. Check capacities, supplies, and product compatibility.'
        }


# Background thread processor for jobs
def process_job_in_background(job_id, network_id, nodes, transport_cost_per_km, excel_file_path=None):
    update_job_status(job_id, 'PROCESSING')
    start_time = time.time()
    
    try:
        farmers = [n for n in nodes if n['type'] == 'farmer']
        hubs = [n for n in nodes if n['type'] == 'hub']
        plants = [n for n in nodes if n['type'] == 'plant']
        geographies = [n for n in nodes if n['type'] == 'geography']
        
        # Run solver helper
        res = solve_network_lp(farmers, hubs, plants, geographies, transport_cost_per_km, excel_file_path)
        
        if res.get('status') in ('OPTIMAL', 'FEASIBLE'):
            vehicle_limits_map = parse_bmc_vehicles(excel_file_path)
            plant_bmc_mapping = parse_plant_bmc_mapping(excel_file_path)
            valid_route_tuples = {(str(bmc), str(plant), str(commodity)) for plant, bmc, commodity in plant_bmc_mapping}
            
            # Map BMCs to Suppliers (need to extract from mapping file if not available otherwise)
            bmc_to_supplier = {}
            if excel_file_path and os.path.exists(excel_file_path):
                try:
                    df_map = pd.read_excel(excel_file_path, sheet_name='Plant_BMC_Mapping')
                    if 'Supplier' in df_map.columns:
                        bmc_to_supplier = df_map.drop_duplicates(subset=['BMCCode']).set_index('BMCCode')['Supplier'].to_dict()
                except:
                    pass

            output_filename = f"results_{job_id}.xlsx"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            # Initialize sub-cluster vehicle pools
            subcluster_vehicle_pools = {}
            for supplier_id, info in vehicle_limits_map.items():
                if not isinstance(info, dict) or 'limits' not in info:
                    continue
                c = info.get('cluster', '')
                sc = info.get('subcluster', '')
                key = (c, sc)
                if key not in subcluster_vehicle_pools:
                    subcluster_vehicle_pools[key] = {vc: 0.0 for vc in vehicle_limits_map.get('global_caps', {}).keys()}
                limits = info['limits']
                for vc in vehicle_limits_map.get('global_caps', {}).keys():
                    subcluster_vehicle_pools[key][vc] += limits.get(vc, 0.0)

            # Find BMC capacities
            bmc_capacities = {}
            for h in hubs:
                h_prods = h.get('products', [])
                if not h_prods and 'capacity' in h:
                    h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity']}]
                for p in h_prods:
                    if 'type' in p:
                        bmc_capacities[(h['id'], p['type'])] = p.get('capacity', 0.0)

            # Calculate total flow from each BMC for each milk type
            total_flow_from_bmc = {}
            for r in res.get('routes', []):
                if r.get('from_type') == 'hub':
                    key = (r['from_id'], r['product_type'])
                    total_flow_from_bmc[key] = total_flow_from_bmc.get(key, 0.0) + r['flow']

            # Separate Hub -> Plant routes and sort them by cluster/subcluster and flow (descending)
            hub_routes = [r for r in res.get('routes', []) if r.get('from_type') == 'hub']
            
            # Helper to get cluster and subcluster for sorting and grouping
            def get_subcluster_key(r):
                supplier = bmc_to_supplier.get(r['from_id'], '')
                bmc_info = vehicle_limits_map.get(supplier, {})
                c = bmc_info.get('cluster', '') if isinstance(bmc_info, dict) else ''
                sc = bmc_info.get('subcluster', '') if isinstance(bmc_info, dict) else ''
                return (c, sc)
                
            hub_routes.sort(key=lambda x: (get_subcluster_key(x), -x['flow']))

            # Process Hub -> Plant routes using sub-cluster pools and supply rules
            for r in hub_routes:
                c, sc = get_subcluster_key(r)
                key = (c, sc)
                
                # Retrieve remaining sub-cluster vehicle pool
                limits = subcluster_vehicle_pools.get(key, {
                    vc: 1000000.0 for vc in vehicle_limits_map.get('global_caps', {}).keys()
                })
                
                # Margins
                supplier = bmc_to_supplier.get(r['from_id'], '')
                bmc_info = vehicle_limits_map.get(supplier, {})
                margin_low = bmc_info.get('margin_low', 5.0) if isinstance(bmc_info, dict) else 5.0
                margin_high = bmc_info.get('margin_high', 5.0) if isinstance(bmc_info, dict) else 5.0
                strategy = bmc_info.get('strategy', 'Whole Milk Supply') if isinstance(bmc_info, dict) else 'Whole Milk Supply'
                
                # Margins for output columns
                r['margin_low'] = margin_low
                r['margin_high'] = margin_high
                
                # Min and max flow quantities
                q = r['flow']
                min_flow = q * (1.0 - margin_high / 100.0)
                max_flow = q * (1.0 + margin_low / 100.0)
                r['min_flow_quantity'] = min_flow
                r['max_flow_quantity'] = max_flow
                
                # Left quantity on BMC
                left_qty = bmc_capacities.get((r['from_id'], r['product_type']), 0.0) - total_flow_from_bmc.get((r['from_id'], r['product_type']), 0.0)
                
                # Temporary vehicle allocation
                optimal_veh = get_optimal_vehicles(q, limits, caps=vehicle_limits_map.get('global_caps'), distance=r['distance'], strategy=strategy, margin=margin_high)
                global_caps = vehicle_limits_map.get('global_caps', {})
                for vc in global_caps.keys():
                    r[f'vehicles_{vc}'] = optimal_veh.get(vc, 0)
                total_veh = sum(optimal_veh.values())
                total_cap = sum(count * global_caps.get(v, 0) for v, count in optimal_veh.items())
                excess_qty = total_cap - q if total_veh > 0 else 0.0
                
                # ── Vehicle Dispatch Rule ───────────────────────────────────────────────
                # When dispatching 1 or more vehicles, vehicles are loaded largest-first.
                # All vehicles except the LAST are fully loaded (empty = 0).
                # The LAST (partial) vehicle may have empty space — and that empty space
                # CANNOT exceed LeaveQuantity (lq_val).
                #
                #   partial_vehicle_empty = total_cap - flow   (= excess_qty when ≥ 0)
                #
                # If the round-up result has excess_qty > lq_val → switch to round-DOWN:
                #   All vehicles carry their full capacity (each empty = 0 ≤ lq_val ✓).
                #   Any deficit (flow - total_cap) is left at the BMC.
                # ────────────────────────────────────────────────────────────────────────

                do_not_supply  = False
                reason_override = None
                per_veh_empty  = max(0.0, excess_qty)   # default: partial vehicle empty

                # Determine last allocated vehicle (smallest capacity utilized)
                lq_val = None
                if optimal_veh:
                    global_caps = vehicle_limits_map.get('global_caps', {'7 L': 7000.0, '10 L': 10000.0, '12L': 12000.0, '15 L': 15000.0, '18 L': 18000.0})
                    smallest_cap = min((global_caps.get(k, 0) for k, v in optimal_veh.items() if v > 0), default=None)
                    if smallest_cap:
                        lq_val = 0.15 * smallest_cap

                if total_veh == 0 and q > 0.1:
                    do_not_supply = True
                    reason_override = "No vehicles available in the sub-cluster pool"

                elif lq_val is not None and excess_qty > lq_val:
                    # The last (partial) vehicle would be too empty → switch to round-DOWN.
                    # Round-down: maximise total capacity WITHOUT exceeding flow.
                    # Result: every vehicle runs fully loaded (empty = 0 ≤ lq_val).
                    rd_veh = get_vehicles_round_down(q, limits, caps=vehicle_limits_map.get('global_caps'))
                    global_caps = vehicle_limits_map.get('global_caps', {})
                    rd_total_veh = sum(rd_veh.values())
                    rd_total_cap = sum(count * global_caps.get(v, 0) for v, count in rd_veh.items())

                    if rd_total_veh > 0:
                        for vc in global_caps.keys():
                            r[f'vehicles_{vc}'] = rd_veh.get(vc, 0)
                        
                        optimal_veh = rd_veh
                            
                        total_veh   = rd_total_veh
                        total_cap   = rd_total_cap
                        excess_qty  = rd_total_cap - q
                        per_veh_empty = 0.0
                        deficit     = q - rd_total_cap
                        reason_override = (
                            f"Supplied — all {total_veh} vehicle(s) fully loaded; "
                            f"{deficit:.0f} L left at BMC | "
                            f"each vehicle empty = 0 L ≤ LQ {lq_val:.0f} L"
                        )
                    else:
                        min_cap = min((c for c in global_caps.values() if c > 0), default=10000.0)
                        do_not_supply = True
                        reason_override = (
                            f"Cannot supply: flow ({q:.0f} L) requires {min_cap:.0f} L vehicle but excess empty space exceeds {lq_val:.0f} L (15% rule)"
                        )

                # ── Apply decision ───────────────────────────────────────────────────────
                if do_not_supply:
                    global_caps = vehicle_limits_map.get('global_caps', {})
                    for vc in global_caps.keys():
                        r[f'vehicles_{vc}'] = 0
                    r['total_vehicles']       = 0
                    r['total_vehicle_capacity'] = 0.0
                    r['excess_vehicle_capacity'] = 0.0
                    r['per_vehicle_empty']    = 0.0
                    r['vehicle_reason']       = reason_override
                else:
                    # Build reason for the normal supply path (excess_qty ≤ lq_val)
                    if not reason_override:
                        if lq_val is not None:
                            reason_override = (
                                f"Supplied: partial vehicle empty {per_veh_empty:.0f} L "
                                f"≤ LQ {lq_val:.0f} L"
                            )
                        else:
                            reason_override = "Supplied"

                    r['total_vehicles']       = total_veh
                    r['total_vehicle_capacity'] = total_cap
                    r['excess_vehicle_capacity'] = round(excess_qty, 2)
                    r['per_vehicle_empty']    = round(per_veh_empty, 2)
                    r['vehicle_reason']       = reason_override

                    # Decrement from pool


            # For non-hub routes, add default columns
            for r in res.get('routes', []):
                if r.get('from_type') != 'hub':
                    global_caps = vehicle_limits_map.get('global_caps', {})
                    for vc in global_caps.keys():
                        r[f'vehicles_{vc}'] = 0
                    r['total_vehicles'] = 0
                    r['total_vehicle_capacity'] = 0.0
                    r['excess_vehicle_capacity'] = 0.0
                    r['per_vehicle_empty'] = 0.0
                    r['vehicle_reason'] = "N/A"
                    r['margin_low'] = 0.0
                    r['margin_high'] = 0.0
                    r['min_flow_quantity'] = r['flow']
                    r['max_flow_quantity'] = r['flow']

            # 1. Summary Sheet
            summary_data = [
                {'Metric': 'Solver Status', 'Value': res['status']},
                {'Metric': 'Net Daily Profit (₹)', 'Value': res['summary']['profit']},
                {'Metric': 'Total Revenue (₹)', 'Value': res['summary']['revenue']},
                {'Metric': 'Total Transport Cost (₹)', 'Value': res['summary']['transport_cost']},
                {'Metric': 'Total Processing Cost (₹)', 'Value': res['summary']['processing_cost']},
                {'Metric': 'Hub Processing Cost (₹)', 'Value': res['summary']['hub_processing_cost']},
                {'Metric': 'Plant Processing Cost (₹)', 'Value': res['summary']['plant_processing_cost']},
                {'Metric': 'Total Nodes', 'Value': len(nodes)}
            ]
            
            # Calculate total flows by milk type
            flow_by_type = {}
            for r in res.get('routes', []):
                if r.get('from_type') == 'hub':
                    m = r.get('product_type', 'Unknown')
                    flow_by_type[m] = flow_by_type.get(m, 0.0) + r.get('flow', 0.0)
                    
            for m, total in flow_by_type.items():
                summary_data.append({'Metric': f'Total Flow - {m} (L)', 'Value': round(total, 2)})
                
            summary_data.append({'Metric': 'Processing Time (seconds)', 'Value': round(time.time() - start_time, 2)})
            
            df_summary = pd.DataFrame(summary_data)
            
            # 2. Nodes Sheet (Long Format)
            nodes_data = []
            
            inflow_lookup = {}
            outflow_lookup = {}
            for r in res.get('routes', []):
                fid = r['from_id']
                tid = r['to_id']
                ptype = r['product_type']
                flow_val = r['flow']
                
                inflow_lookup[(tid, ptype)] = inflow_lookup.get((tid, ptype), 0.0) + flow_val
                outflow_lookup[(fid, ptype)] = outflow_lookup.get((fid, ptype), 0.0) + flow_val

            for n in nodes:
                nid = n['id']
                ntype = n['type']
                
                if ntype == 'farmer':
                    continue
                elif ntype == 'hub':
                    for p in n.get('products', []):
                        comm = p['type']
                        limit = p.get('capacity', 0.0)
                        inflow = inflow_lookup.get((nid, comm), 0.0)
                        outflow = outflow_lookup.get((nid, comm), 0.0)
                        nodes_data.append({
                            'Node ID': nid,
                            'Name': n['name'],
                            'Type': ntype,
                            'Subtype': n.get('subtype', ''),
                            'Latitude': n['lat'],
                            'Longitude': n['lng'],
                            'Commodity': comm,
                            'Inflow Throughput': round(inflow, 2),
                            'Outflow Throughput': round(outflow, 2),
                            'Capacity / Supply Limit': limit,
                                                    })
                elif ntype == 'plant':
                    p_demands = n.get('demands', [])
                    if p_demands:
                        for d in p_demands:
                            comm = d['type']
                            limit = d.get('demand', 0.0)
                            inflow = inflow_lookup.get((nid, comm), 0.0)
                            nodes_data.append({
                                'Node ID': nid,
                                'Name': n['name'],
                                'Type': ntype,
                                'Subtype': n.get('subtype', ''),
                                'Latitude': n['lat'],
                                'Longitude': n['lng'],
                                'Commodity': comm,
                                'Inflow Throughput': round(inflow, 2),
                                'Outflow Throughput': round(inflow, 2),
                                'Capacity / Supply Limit': limit,
                                                            })
                    else:
                        for m in n.get('inflow_milks', []):
                            comm = m['type']
                            limit = m.get('capacity', 0.0)
                            inflow = inflow_lookup.get((nid, comm), 0.0)
                            outflow = outflow_lookup.get((nid, comm), 0.0)
                            nodes_data.append({
                                'Node ID': nid,
                                'Name': n['name'],
                                'Type': ntype,
                                'Subtype': n.get('subtype', ''),
                                'Latitude': n['lat'],
                                'Longitude': n['lng'],
                                'Commodity': comm,
                                'Inflow Throughput': round(inflow, 2),
                                'Outflow Throughput': round(outflow, 2),
                                'Capacity / Supply Limit': limit,
                                                            })
                        for p in n.get('products', []):
                            comm = p['type']
                            limit = p.get('yield', 0.0)
                            inflow = inflow_lookup.get((nid, comm), 0.0)
                            outflow = outflow_lookup.get((nid, comm), 0.0)
                            nodes_data.append({
                                'Node ID': nid,
                                'Name': n['name'],
                                'Type': ntype,
                                'Subtype': n.get('subtype', ''),
                                'Latitude': n['lat'],
                                'Longitude': n['lng'],
                                'Commodity': comm,
                                'Inflow Throughput': round(inflow, 2),
                                'Outflow Throughput': round(outflow, 2),
                                'Capacity / Supply Limit': limit,
                                                            })
                elif ntype == 'geography':
                    for p in n.get('products', []):
                        comm = p['type']
                        limit = p.get('demand', 0.0)
                        inflow = inflow_lookup.get((nid, comm), 0.0)
                        outflow = outflow_lookup.get((nid, comm), 0.0)
                        nodes_data.append({
                            'Node ID': nid,
                            'Name': n['name'],
                            'Type': ntype,
                            'Subtype': n.get('subtype', ''),
                            'Latitude': n['lat'],
                            'Longitude': n['lng'],
                            'Commodity': comm,
                            'Inflow Throughput': round(inflow, 2),
                            'Outflow Throughput': round(outflow, 2),
                            'Capacity / Supply Limit': limit,
                                                    })
            df_nodes = pd.DataFrame(nodes_data)
            
            # Calculate plant-level substitution values from the solver
            plant_subs = {}
            for nd in nodes_data:
                if nd['Type'] == 'plant':
                    pid = nd['Node ID']
                    if pid not in plant_subs:
                        plant_subs[pid] = {
                            'BM_to_FCM': res.get('trans_vars_solution', {}).get((pid, 'BM_to_FCM'), 0.0),
                            'FCM_to_MM': res.get('trans_vars_solution', {}).get((pid, 'FCM_to_MM'), 0.0),
                            'BM_inflow': 0.0,
                            'FCM_inflow': 0.0
                        }
                    
                    comm = str(nd['Commodity']).lower()
                    inflow = nd['Inflow Throughput']
                    if 'buffalo' in comm or 'bm' in comm:
                        plant_subs[pid]['BM_inflow'] += inflow
                    elif 'fcm' in comm:
                        plant_subs[pid]['FCM_inflow'] += inflow
            
            # Since BM_to_FCM might cascade further to MM, we calculate how much BM went to MM
            # The amount of BM that goes to MM is any FCM_to_MM that exceeds physical FCM inflow.
            # But the plant pools them.
            for pid, subs in plant_subs.items():
                bm_to_fcm = subs['BM_to_FCM']
                fcm_to_mm = subs['FCM_to_MM']
                physical_fcm = subs['FCM_inflow']
                
                fcm_cascaded = min(fcm_to_mm, physical_fcm)
                bm_cascaded_to_mm = max(0, fcm_to_mm - physical_fcm)
                bm_cascaded_to_fcm = max(0, bm_to_fcm - bm_cascaded_to_mm)
                
                subs['BM_to_FCM_actual'] = bm_cascaded_to_fcm
                subs['BM_to_MM_actual'] = bm_cascaded_to_mm
                subs['FCM_to_MM_actual'] = fcm_cascaded
            
            # 3. Routes Sheet (Active and Unused/Candidate Routes)
            routes_data = []
            
            # Map of active routes to easily find flow details and avoid duplicates
            active_keys = {(r['from_id'], r['to_id'], r['product_type']) for r in res.get('routes', [])}
            
            # Populate active routes
            for r in res.get('routes', []):
                from_node = next((n for n in nodes if n['id'] == r['from_id']), {'name': 'Unknown'})
                to_node = next((n for n in nodes if n['id'] == r['to_id']), {'name': 'Unknown'})
                
                supplier = bmc_to_supplier.get(r['from_id'], '') if r['from_type'] == 'hub' else ''
                bmc_info = vehicle_limits_map.get(supplier, {}) if r['from_type'] == 'hub' else {}
                lq = bmc_info.get('leave_quantity', 0.0) if isinstance(bmc_info, dict) else 0.0
                cluster = bmc_info.get('cluster', '') if isinstance(bmc_info, dict) else ''
                subcluster = bmc_info.get('subcluster', '') if isinstance(bmc_info, dict) else ''
                strategy = bmc_info.get('strategy', '') if isinstance(bmc_info, dict) else ''
                
                ptype = r['product_type']
                ptype_lower = str(ptype).lower()
                
                # Default primary row values
                primary_flow = r['flow']
                extra_flows = [] # List of tuples: (flow, product_type, reason)
                
                if r['to_type'] == 'plant' and r['to_id'] in plant_subs:
                    subs = plant_subs[r['to_id']]
                    
                    if ('buffalo' in ptype_lower or 'bm' in ptype_lower) and subs['BM_inflow'] > 0:
                        prop = r['flow'] / subs['BM_inflow']
                        r_bm_to_fcm = prop * subs['BM_to_FCM_actual']
                        r_bm_to_mm = prop * subs['BM_to_MM_actual']
                        
                        primary_flow -= (r_bm_to_fcm + r_bm_to_mm)
                        if round(r_bm_to_fcm, 2) > 0:
                            extra_flows.append((r_bm_to_fcm, f"{ptype} to FCM", "Optimal Flow (Substituted to FCM)"))
                        if round(r_bm_to_mm, 2) > 0:
                            extra_flows.append((r_bm_to_mm, f"{ptype} to MM", "Optimal Flow (Substituted to MM)"))
                            
                    elif 'fcm' in ptype_lower and subs['FCM_inflow'] > 0:
                        prop = r['flow'] / subs['FCM_inflow']
                        r_fcm_to_mm = prop * subs['FCM_to_MM_actual']
                        
                        primary_flow -= r_fcm_to_mm
                        if round(r_fcm_to_mm, 2) > 0:
                            extra_flows.append((r_fcm_to_mm, f"{ptype} to MM", "Optimal Flow (Substituted to MM)"))
                
                # Append primary row
                if round(primary_flow, 2) > 0 or not extra_flows:
                    routes_data.append({
                        'Route ID': r['id'],
                        'From Node ID': r['from_id'],
                        'From Name': from_node.get('name', 'Unknown'),
                        'From Type': r['from_type'],
                        'From Latitude': from_node.get('lat'),
                        'From Longitude': from_node.get('lng'),
                        'To Node ID': r['to_id'],
                        'To Name': to_node.get('name', 'Unknown'),
                        'To Type': r['to_type'],
                        'To Latitude': to_node.get('lat'),
                        'To Longitude': to_node.get('lng'),
                        'Product / Milk Type': ptype,
                        'Flow': max(0.0, round(primary_flow, 2)),
                        'Unit': r['unit'],
                        'Distance (km)': r['distance'],
                        'Transport Cost (₹)': r['cost'],
                        'Status': 'ACTIVE',
                        'Reason': 'Optimal Flow',
                        **{f'{vc} Vehicles': r.get(f'vehicles_{vc}', 0) for vc in vehicle_limits_map.get('global_caps', {}).keys()},
                        'Total Vehicles': r.get('vehicles_total', 0) if 'vehicles_total' in r else r.get('total_vehicles', 0),
                        'Total Vehicle Capacity (L)': r.get('capacity_total', 0) if 'capacity_total' in r else r.get('total_vehicle_capacity', 0),
                        'Excess Vehicle Capacity (L)': r.get('capacity_excess', 0) if 'capacity_excess' in r else r.get('excess_vehicle_capacity', 0),
                        'VehicleReason': r.get('vehicle_reason', 'Optimal'),
                                                'SupplierCluster': cluster,
                        'SupplierSubCluster': subcluster,
                        'Strategy': strategy,
                        'FlowLowMarginPercentage': bmc_info.get('margin_low', 0.0) if isinstance(bmc_info, dict) else 5.0,
                        'FlowHighMarginPercentage': bmc_info.get('margin_high', 0.0) if isinstance(bmc_info, dict) else 5.0,
                        'MinimumFlowQuantity': bmc_info.get('min_flow', 0.0) if isinstance(bmc_info, dict) else 0.0,
                        'MaximumFlowQuantity': bmc_info.get('max_flow', 0.0) if isinstance(bmc_info, dict) else 0.0,
                        'Mapping Exists': 'Yes' if (str(r['from_id']), str(r['to_id']), str(ptype)) in valid_route_tuples else 'No'
                    })
                
                # Append extra rows if any substitution occurred
                for ext_flow, ext_ptype, ext_reason in extra_flows:
                    routes_data.append({
                        'Route ID': r['id'] + "_extra",
                        'From Node ID': r['from_id'],
                        'From Name': from_node.get('name', 'Unknown'),
                        'From Type': r['from_type'],
                        'From Latitude': from_node.get('lat'),
                        'From Longitude': from_node.get('lng'),
                        'To Node ID': r['to_id'],
                        'To Name': to_node.get('name', 'Unknown'),
                        'To Type': r['to_type'],
                        'To Latitude': to_node.get('lat'),
                        'To Longitude': to_node.get('lng'),
                        'Product / Milk Type': ext_ptype,
                        'Flow': round(ext_flow, 2),
                        'Unit': r['unit'],
                        'Distance (km)': r['distance'],
                        'Transport Cost (₹)': 0.0,
                        'Status': 'ACTIVE',
                        'Reason': ext_reason,
                        **{f'{vc} Vehicles': 0 for vc in vehicle_limits_map.get('global_caps', {}).keys()},
                        'Total Vehicles': 0,
                        'Total Vehicle Capacity (L)': 0,
                        'Excess Vehicle Capacity (L)': 0,
                        'VehicleReason': 'Substituted Flow',
                                                'SupplierCluster': cluster,
                        'SupplierSubCluster': subcluster,
                        'Strategy': strategy,
                        'FlowLowMarginPercentage': 0.0,
                        'FlowHighMarginPercentage': 0.0,
                        'MinimumFlowQuantity': 0.0,
                        'MaximumFlowQuantity': 0.0,
                        'Mapping Exists': 'Yes' if (str(r['from_id']), str(r['to_id']), str(ext_ptype)) in valid_route_tuples else 'No'
                    })

            # Pre-calculate lookup dictionaries for node capacities and demands
            hub_capacities = {}
            for h in hubs:
                h_prods = h.get('products', [])
                if not h_prods and 'capacity' in h:
                    h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity']}]
                for p in h_prods:
                    if 'type' in p:
                        hub_capacities[(h['id'], p['type'])] = p.get('capacity', 0.0)

            plant_capacities = {}
            for p in plants:
                p_demands = p.get('demands', [])
                if p_demands:
                    for d in p_demands:
                        plant_capacities[(p['id'], d['type'])] = d.get('demand', 0.0)
                else:
                    inflow_milks = p.get('inflow_milks', [])
                    if not inflow_milks:
                        inflow_milks = [
                            {'type': 'Cow Milk', 'capacity': p.get('capacity', 10000)},
                            {'type': 'Buffalo Milk', 'capacity': p.get('capacity', 10000)}
                        ]
                    for m in inflow_milks:
                        if 'type' in m:
                            plant_capacities[(p['id'], m['type'])] = m.get('capacity', 0.0)

            geo_demands = {}
            for g in geographies:
                g_products = g.get('products', [])
                if not g_products and 'product_type' in g:
                    g_products = [{'type': g['product_type'], 'demand': g.get('demand', 0)}]
                for prod in g_products:
                    if 'type' in prod:
                        geo_demands[(g['id'], prod['type'])] = prod.get('demand', 0.0)

            # 3.1. Generate Unused Routes: Hub -> Plant
            for h in hubs:
                h_prods = h.get('products', [])
                if not h_prods and 'capacity' in h:
                    h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity']}]
                for p in h_prods:
                    m = p.get('type')
                    if not m:
                        continue
                    for plant in plants:
                        p_demands = plant.get('demands', [])
                        plant_demand_types = {d['type'] for d in p_demands if 'type' in d}
                        
                        inflow_milks = plant.get('inflow_milks', [])
                        if not inflow_milks:
                            inflow_milks = [{'type': 'Cow Milk'}, {'type': 'Buffalo Milk'}]
                        plant_milk_types = {im['type'] for im in inflow_milks if 'type' in im}
                        
                        if m in plant_milk_types or m in plant_demand_types:
                            key = (h['id'], plant['id'], m)
                            if key not in active_keys:
                                total_h_out = outflow_lookup.get((h['id'], m), 0.0)
                                total_p_in = inflow_lookup.get((plant['id'], m), 0.0)
                                plant_cap = plant_capacities.get((plant['id'], m), 0.0)
                                hub_cap = hub_capacities.get((h['id'], m), 0.0)
                                
                                pair_key = tuple(sorted([h['id'], plant['id']]))
                                dist = _distance_cache.get(pair_key)
                                if dist is None:
                                    dist = calculate_haversine_distance(h, plant)
                                    
                                if dist > MAX_DISTANCE_LIMIT:
                                    reason = f"Distance exceeds {int(MAX_DISTANCE_LIMIT)} km"
                                elif hub_cap <= 0:
                                    reason = "BMC capacity is zero"
                                elif plant_cap <= 0:
                                    reason = "Plant capacity/demand for this milk type is zero"
                                elif abs(total_h_out - hub_cap) < 0.1:
                                    reason = "BMC capacity is fully utilized by other Plants"
                                elif abs(total_p_in - plant_cap) < 0.1:
                                    reason = "Plant capacity/demand is fully utilized by other BMCs"
                                else:
                                    reason = "Mapping not exists."
                                routes_data.append({
                                    'Route ID': f"route_{h['id']}_{plant['id']}_{m.replace(' ', '_')}",
                                    'From Node ID': h['id'],
                                    'From Name': h.get('name', 'Unknown'),
                                    'From Type': 'hub',
                                    'From Latitude': h.get('lat'),
                                    'From Longitude': h.get('lng'),
                                    'To Node ID': plant['id'],
                                    'To Name': plant.get('name', 'Unknown'),
                                    'To Type': 'plant',
                                    'To Latitude': plant.get('lat'),
                                    'To Longitude': plant.get('lng'),
                                    'Product / Milk Type': m,
                                    'Flow': 0.0,
                                    'Unit': 'L',
                                    'Distance (km)': round(dist, 2),
                                    'Transport Cost (₹)': 0.0,
                                    'Status': 'UNUSED',
                                    'Reason': reason,
                                    'Total Vehicles': 0,
                                    'Total Vehicle Capacity (L)': 0,
                                    'Excess Vehicle Capacity (L)': 0,
                                    'VehicleReason': 'Unused Route',
                                                                        'SupplierCluster': vehicle_limits_map.get(bmc_to_supplier.get(h['id'], ''), {}).get('cluster', '') if isinstance(vehicle_limits_map.get(bmc_to_supplier.get(h['id'], '')), dict) else '',
                                    'SupplierSubCluster': vehicle_limits_map.get(bmc_to_supplier.get(h['id'], ''), {}).get('subcluster', '') if isinstance(vehicle_limits_map.get(bmc_to_supplier.get(h['id'], '')), dict) else '',
                                    'Strategy': vehicle_limits_map.get(bmc_to_supplier.get(h['id'], ''), {}).get('strategy', '') if isinstance(vehicle_limits_map.get(bmc_to_supplier.get(h['id'], '')), dict) else '',
                                    'FlowLowMarginPercentage': vehicle_limits_map.get(bmc_to_supplier.get(h['id'], ''), {}).get('margin_low', 0.0) if isinstance(vehicle_limits_map.get(bmc_to_supplier.get(h['id'], '')), dict) else 5.0,
                                    'FlowHighMarginPercentage': vehicle_limits_map.get(bmc_to_supplier.get(h['id'], ''), {}).get('margin_high', 0.0) if isinstance(vehicle_limits_map.get(bmc_to_supplier.get(h['id'], '')), dict) else 5.0,
                                    'MinimumFlowQuantity': 0.0,
                                    'MaximumFlowQuantity': 0.0,
                                    'Mapping Exists': 'Yes' if (str(h['id']), str(plant['id']), str(m)) in valid_route_tuples else 'No'
                                })

            # 3.2. Generate Unused Routes: Plant -> Geography
            if geographies:
                for plant in plants:
                    p_products = plant.get('products', [])
                    if not p_products and 'production_type' in plant:
                        p_products = [{'type': plant['production_type']}]
                    for p in p_products:
                        ptype = p.get('type')
                        if not ptype:
                            continue
                        raw_milk = get_milk_type_for_product(ptype)
                        for g in geographies:
                            g_products = g.get('products', [])
                            if not g_products and 'product_type' in g:
                                g_products = [{'type': g['product_type']}]
                            g_types = {gp['type'] for gp in g_products if 'type' in gp}
                            
                            if ptype in g_types:
                                key = (plant['id'], g['id'], ptype)
                                if key not in active_keys:
                                    total_p_in = inflow_lookup.get((plant['id'], raw_milk), 0.0)
                                    total_g_in = inflow_lookup.get((g['id'], ptype), 0.0)
                                    g_demand = geo_demands.get((g['id'], ptype), 0.0)
                                    
                                    pair_key = tuple(sorted([plant['id'], g['id']]))
                                    dist = _distance_cache.get(pair_key)
                                    if dist is None:
                                        dist = calculate_haversine_distance(plant, g)
                                        
                                    if dist > MAX_DISTANCE_LIMIT:
                                        reason = f"Distance exceeds {int(MAX_DISTANCE_LIMIT)} km"
                                    elif total_p_in == 0:
                                        reason = "Plant has no raw milk inflow to process"
                                    elif g_demand <= 0:
                                        reason = "Market demand for this product is zero"
                                    elif abs(total_g_in - g_demand) < 0.1:
                                        reason = "Market demand is fully satisfied by other Plants"
                                    else:
                                        reason = "Mapping not exists."
                                    unit = 'kg' if any(k in ptype.lower() for k in ['cheese', 'khoya', 'butter', 'milk powder']) else 'L'
                                    routes_data.append({
                                        'Route ID': f"route_{plant['id']}_{g['id']}_{ptype.replace(' ', '_')}",
                                        'From Node ID': plant['id'],
                                        'From Name': plant.get('name', 'Unknown'),
                                        'From Type': 'plant',
                                        'From Latitude': plant.get('lat'),
                                        'From Longitude': plant.get('lng'),
                                        'To Node ID': g['id'],
                                        'To Name': g.get('name', 'Unknown'),
                                        'To Type': 'geography',
                                        'To Latitude': g.get('lat'),
                                        'To Longitude': g.get('lng'),
                                        'Product / Milk Type': ptype,
                                        'Flow': 0.0,
                                        'Unit': unit,
                                        'Distance (km)': round(dist, 2),
                                        'Transport Cost (₹)': 0.0,
                                        'Status': 'UNUSED',
                                        'Reason': reason,
                                        'Total Vehicles': 0,
                                        'Total Vehicle Capacity (L)': 0,
                                        'Excess Vehicle Capacity (L)': 0,
                                        'VehicleReason': 'N/A',
                                                                                'SupplierCluster': '',
                                        'SupplierSubCluster': '',
                                        'Strategy': '',
                                        'FlowLowMarginPercentage': 0.0,
                                        'FlowHighMarginPercentage': 0.0,
                                        'MinimumFlowQuantity': 0.0,
                                        'MaximumFlowQuantity': 0.0,
                                        'Mapping Exists': 'Yes' if (str(plant['id']), str(g['id']), str(ptype)) in valid_route_tuples else 'No'
                                    })

            df_routes = pd.DataFrame(routes_data)
            
            # --- 1. Plant Consumption Report ---
            df_hub_to_plant = df_routes[
                (df_routes['Status'] == 'ACTIVE') & 
                (df_routes['From Type'] == 'hub') & 
                (df_routes['To Type'] == 'plant')
            ]
            
            unique_comms_set = set(df_nodes['Commodity'].unique()) if not df_nodes.empty else set()
            for _, r in df_hub_to_plant.iterrows():
                unique_comms_set.add(r['Product / Milk Type'])
            unique_commodities = sorted(list(unique_comms_set))
            
            plant_report_rows = []
            for p in plants:
                row_dict = {'Plant ID': p['id'], 'Plant Name': p.get('name', p['id'])}
                plant_supplies = {}
                for _, r in df_hub_to_plant.iterrows():
                    if r['To Node ID'] == p['id']:
                        c = r['Product / Milk Type']
                        plant_supplies[c] = plant_supplies.get(c, 0.0) + r['Flow']
                        
                p_demands = p.get('demands', [])
                plant_demands = {}
                if p_demands:
                    for d in p_demands:
                        plant_demands[d['type']] = d.get('demand', 0.0)
                else:
                    inflow_milks = p.get('inflow_milks', [])
                    if not inflow_milks:
                        inflow_milks = [{'type': 'Cow Milk', 'capacity': p.get('capacity', 10000)},
                                        {'type': 'Buffalo Milk', 'capacity': p.get('capacity', 10000)}]
                    for m in inflow_milks:
                        if 'type' in m:
                            plant_demands[m['type']] = m.get('capacity', 0.0)
                
                for comm in unique_commodities:
                    demand = plant_demands.get(comm, 0.0)
                    supply = plant_supplies.get(comm, 0.0)
                    if demand == 0:
                        pct = ""
                    else:
                        pct = round((supply / demand * 100.0), 2)
                    
                    row_dict[f'{comm} {{Demand}}'] = demand
                    row_dict[f'{comm} {{Supply}}'] = supply
                    row_dict[f'{comm} {{Received Percentage}}'] = pct
                plant_report_rows.append(row_dict)
            df_plant_report = pd.DataFrame(plant_report_rows)
            if df_plant_report.empty:
                df_plant_report = pd.DataFrame(columns=['Plant ID', 'Plant Name'])
            
            # --- 2. BMC Supply Report ---
            hub_report_rows = []
            for h in hubs:
                supplier = bmc_to_supplier.get(h['id'], '')
                row_dict = {
                    'BMC ID': h['id'],
                    'BMC Name': h.get('name', h['id']),
                                    }
                
                hub_supplies = {}
                for _, r in df_hub_to_plant.iterrows():
                    if r['From Node ID'] == h['id']:
                        c = r['Product / Milk Type']
                        hub_supplies[c] = hub_supplies.get(c, 0.0) + r['Flow']
                        
                h_prods = h.get('products', [])
                hub_stocks = {}
                if not h_prods and 'capacity' in h:
                    h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity']}]
                for p_item in h_prods:
                    if p_item.get('type'):
                        hub_stocks[p_item['type']] = p_item.get('capacity', 0.0)
                        
                for comm in unique_commodities:
                    stock = hub_stocks.get(comm, 0.0)
                    supply = hub_supplies.get(comm, 0.0)
                    if stock == 0:
                        pct = ""
                    else:
                        pct = round((supply / stock * 100.0), 2)
                        
                    row_dict[f'{comm} {{Stock}}'] = stock
                    row_dict[f'{comm} {{Supply}}'] = supply
                    row_dict[f'{comm} {{Supply Percentage}}'] = pct
                hub_report_rows.append(row_dict)
            df_hub_report = pd.DataFrame(hub_report_rows)
            if df_hub_report.empty:
                df_hub_report = pd.DataFrame(columns=['BMC ID', 'BMC Name'])
                
            # --- 3. Hub To Plant (optimal flow Hub -> Plant) ---
            # df_hub_to_plant is already generated above
            
            # --- 4. BMC Wise Allocation Matrix ---
            plant_names_list = []
            seen_plants = set()
            for p in plants:
                name = p.get('name', p['id'])
                if name not in seen_plants:
                    seen_plants.add(name)
                    plant_names_list.append(name)
            
            flow_map = {}
            for _, r in df_hub_to_plant.iterrows():
                key = (r['From Node ID'], r['To Node ID'], r['Product / Milk Type'])
                flow_map[key] = flow_map.get(key, 0.0) + r['Flow']
                    
            bmc_allocation_rows = []
            for h in hubs:
                h_prods = h.get('products', [])
                if not h_prods and 'capacity' in h:
                    h_prods = [{'type': 'Cow Milk', 'capacity': h['capacity']}]
                
                hub_commodities = set()
                for p_item in h_prods:
                    if p_item.get('type'):
                        hub_commodities.add(p_item['type'])
                for (from_id, to_id, prod_type) in flow_map:
                    if from_id == h['id']:
                        hub_commodities.add(prod_type)
                        
                for m in sorted(list(hub_commodities)):
                    total_flow = sum(flow_map.get((h['id'], p['id'], m), 0.0) for p in plants)
                    supplier = bmc_to_supplier.get(h['id'], '')
                    bmc_info = vehicle_limits_map.get(supplier, {})
                    lq = bmc_info.get('leave_quantity', 0.0) if isinstance(bmc_info, dict) else 0.0
                    row_dict = {
                        'BMC': h.get('name', h['id']),
                        'Product': m,
                                                'Quantity': round(total_flow, 2)
                    }
                    for p in plants:
                        p_name = p.get('name', p['id'])
                        flow_val = flow_map.get((h['id'], p['id'], m), 0.0)
                        row_dict[p_name] = round(flow_val, 2)
                    bmc_allocation_rows.append(row_dict)
                    
            df_bmc_wise_alloc = pd.DataFrame(bmc_allocation_rows)
            if not df_bmc_wise_alloc.empty:
                cols = ['BMC', 'Product', 'Quantity'] + [p_name for p_name in plant_names_list if p_name in df_bmc_wise_alloc.columns]
                df_bmc_wise_alloc = df_bmc_wise_alloc.reindex(columns=cols)
            else:
                df_bmc_wise_alloc = pd.DataFrame(columns=['BMC', 'Product', 'Quantity'] + plant_names_list)
 
            # --- 5. Plant Wise Allocation Matrix ---
            bmc_names_list = []
            seen_bmcs = set()
            for h in hubs:
                name = h.get('name', h['id'])
                if name not in seen_bmcs:
                    seen_bmcs.add(name)
                    bmc_names_list.append(name)
                    
            plant_allocation_rows = []
            for p in plants:
                p_commodities = {}
                p_demands = p.get('demands', [])
                if p_demands:
                    for d in p_demands:
                        p_commodities[d['type']] = d.get('demand', 0.0)
                else:
                    inflow_milks = p.get('inflow_milks', [])
                    if not inflow_milks:
                        inflow_milks = [
                            {'type': 'Cow Milk', 'capacity': p.get('capacity', 10000)},
                            {'type': 'Buffalo Milk', 'capacity': p.get('capacity', 10000)}
                        ]
                    for m in inflow_milks:
                        if 'type' in m:
                            p_commodities[m['type']] = m.get('capacity', 0.0)
                            
                for (from_id, to_id, prod_type) in flow_map:
                    if to_id == p['id'] and prod_type not in p_commodities:
                        p_commodities[prod_type] = 0.0
                        
                for m, req_qty in sorted(p_commodities.items()):
                    fulfilled_qty = sum(flow_map.get((h['id'], p['id'], m), 0.0) for h in hubs)
                    if req_qty == 0:
                        pct = ""
                    else:
                        pct = round((fulfilled_qty / req_qty * 100.0), 2)
                        
                    row_dict = {
                        'Plant': p.get('name', p['id']),
                        'Product': m,
                        'Required Quantity': round(req_qty, 2),
                        'Fullfilled Quantity': round(fulfilled_qty, 2),
                        'Fullfilled Percentage': pct
                    }
                    for h in hubs:
                        h_name = h.get('name', h['id'])
                        flow_val = flow_map.get((h['id'], p['id'], m), 0.0)
                        row_dict[h_name] = round(flow_val, 2)
                    plant_allocation_rows.append(row_dict)
                    
            df_plant_wise_alloc = pd.DataFrame(plant_allocation_rows)
            if not df_plant_wise_alloc.empty:
                cols = ['Plant', 'Product', 'Required Quantity', 'Fullfilled Quantity', 'Fullfilled Percentage'] + [h_name for h_name in bmc_names_list if h_name in df_plant_wise_alloc.columns]
                df_plant_wise_alloc = df_plant_wise_alloc.reindex(columns=cols)
            else:
                df_plant_wise_alloc = pd.DataFrame(columns=['Plant', 'Product', 'Required Quantity', 'Fullfilled Quantity', 'Fullfilled Percentage'] + bmc_names_list)
            
            # Save sheets
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
                df_nodes.to_excel(writer, sheet_name='Nodes', index=False)
                df_routes.to_excel(writer, sheet_name='Routes', index=False)
                df_plant_report.to_excel(writer, sheet_name='Plant Consumption Report', index=False)
                df_hub_report.to_excel(writer, sheet_name='BMC Supply Report', index=False)
                df_hub_to_plant.to_excel(writer, sheet_name='Hub To Plant', index=False)
                df_bmc_wise_alloc.to_excel(writer, sheet_name='BMC Wise Allocation', index=False)
                df_plant_wise_alloc.to_excel(writer, sheet_name='Plant Wise Allocation', index=False)
                
                # Create and save a dedicated BMC Vehicle Allocation sheet
                veh_cols = [f'{vc} Vehicles' for vc in vehicle_limits_map.get('global_caps', {}).keys()]
                df_veh_alloc = df_hub_to_plant[[
                    'From Node ID', 'From Name', 'To Node ID', 'To Name', 
                    'Product / Milk Type', 'Flow', 'Unit', 'Distance (km)', 'Transport Cost (₹)'
                ] + veh_cols + [
                    'Total Vehicles', 'Total Vehicle Capacity (L)', 'Excess Vehicle Capacity (L)',
                    'SupplierCluster', 'SupplierSubCluster', 'Strategy',
                    'FlowLowMarginPercentage', 'FlowHighMarginPercentage',
                    'MinimumFlowQuantity', 'MaximumFlowQuantity', 'VehicleReason'
                ]].copy()
                df_veh_alloc = df_veh_alloc.rename(columns={
                    'From Node ID': 'BMC ID',
                    'From Name': 'BMC Name',
                    'To Node ID': 'Plant ID',
                    'To Name': 'Plant Name',
                    'Flow': 'Flow Quantity'
                })
                df_veh_alloc.to_excel(writer, sheet_name='BMC Vehicle Allocation', index=False)
                
            update_job_completed(job_id, output_filename, res['summary'])
        else:
            update_job_failed(job_id, f"Solver solved to infeasible status: {res.get('status')}")
            
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\n{traceback.format_exc()}"
        print("Job processing failed:", error_msg)
        update_job_failed(job_id, error_msg[:1000])


@app.route('/api/optimize', methods=['POST'])
def optimize_network():
    data = request.json
    if not data:
        return jsonify({'status': 'ERROR', 'message': 'No data provided'}), 400

    farmers = data.get('farmers', [])
    hubs = data.get('hubs', [])
    plants = data.get('plants', [])
    geographies = data.get('geographies', [])
    transport_cost_per_km = data.get('transport_cost_per_km', 0.005)

    res = solve_network_lp(farmers, hubs, plants, geographies, transport_cost_per_km)
    if res.get('status') == 'ERROR':
        return jsonify(res), 500
    return jsonify(res)


@app.route('/api/jobs/generate_template', methods=['GET'])
def download_template():
    try:
        df = generate_random_network()
        temp_filename = f"template_{uuid.uuid4().hex[:8]}.xlsx"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        
        # Save nodes in DB under network_id
        network_id = df.iloc[0]['network_id']
        nodes_list = parse_excel_nodes(df)
        
        if db_available:
            try:
                nodes_collection.delete_many({'network_id': network_id})
                nodes_collection.insert_many(nodes_list)
            except Exception as e:
                print("Error saving template nodes to Mongo:", e)
        else:
            global in_memory_nodes
            in_memory_nodes = [n for n in in_memory_nodes if n.get('network_id') != network_id]
            in_memory_nodes.extend(nodes_list)
            
        df.to_excel(temp_path, index=False)
        return send_file(temp_path, as_attachment=True, download_name=f"network_template_{network_id[:8]}.xlsx")
    except Exception as e:
        import traceback
        print("Template generation failed:", traceback.format_exc())
        return jsonify({'status': 'ERROR', 'message': f'Failed to generate template: {str(e)}'}), 500


@app.route('/api/jobs/upload', methods=['POST'])
def upload_job():
    if 'file' not in request.files:
        return jsonify({'status': 'ERROR', 'message': 'No file part in the request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'ERROR', 'message': 'No file selected for uploading'}), 400
        
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        job_id = str(uuid.uuid4())
        input_filename = f"input_{job_id}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, input_filename)
        file.save(file_path)
        
        try:
            nodes = parse_excel_nodes(file_path)
            if not nodes:
                return jsonify({'status': 'ERROR', 'message': 'No valid nodes found in the Excel sheet'}), 400
                
            network_id = nodes[0].get('network_id')
            if not network_id:
                network_id = str(uuid.uuid4())
                for n in nodes:
                    n['network_id'] = network_id
            
            if db_available:
                try:
                    for n in nodes:
                        nodes_collection.replace_one({'id': n['id'], 'network_id': network_id}, n, upsert=True)
                except Exception as e:
                    print("Error saving uploaded nodes to Mongo:", e)
            else:
                global in_memory_nodes
                in_memory_nodes = [n for n in in_memory_nodes if n.get('network_id') != network_id]
                in_memory_nodes.extend(nodes)
                
            job = {
                'job_id': job_id,
                'network_id': network_id,
                'status': 'PENDING',
                'created_at': datetime.datetime.now().isoformat(),
                'completed_at': None,
                'error_message': None,
                'input_filename': input_filename,
                'output_filename': None,
                'result_summary': None,
                'node_count': len(nodes)
            }
            save_new_job(job)
            
            thread = threading.Thread(
                target=process_job_in_background, 
                args=(job_id, network_id, nodes, 0.005, file_path)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'status': 'SUCCESS',
                'message': 'Job uploaded successfully. Solver is running in the background.',
                'job_id': job_id,
                'network_id': network_id
            }), 201
            
        except Exception as e:
            import traceback
            print("Job upload parsing failed:", traceback.format_exc())
            return jsonify({'status': 'ERROR', 'message': f'Failed to parse Excel nodes: {str(e)}'}), 500
            
    return jsonify({'status': 'ERROR', 'message': 'Invalid file format. Please upload an Excel (.xlsx) file.'}), 400


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    jobs = get_all_jobs()
    serialized = []
    for j in jobs:
        j_copy = dict(j)
        j_copy.pop('_id', None)
        serialized.append(j_copy)
    return jsonify(serialized)


@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_job_results(job_id):
    jobs = get_all_jobs()
    job = next((j for j in jobs if j['job_id'] == job_id), None)
    
    if not job:
        return jsonify({'status': 'ERROR', 'message': 'Job not found'}), 404
        
    if job['status'] != 'COMPLETED' or not job['output_filename']:
        return jsonify({'status': 'ERROR', 'message': 'Job results are not ready for download'}), 400
        
    output_path = os.path.join(OUTPUT_FOLDER, job['output_filename'])
    if not os.path.exists(output_path):
        return jsonify({'status': 'ERROR', 'message': 'Result file was not found on server'}), 404
        
    return send_file(output_path, as_attachment=True, download_name=f"network_results_{job_id[:8]}.xlsx")


@app.route('/api/jobs/<job_id>/details', methods=['GET'])
def get_job_details(job_id):
    jobs = get_all_jobs()
    job = next((j for j in jobs if j['job_id'] == job_id), None)
    
    if not job:
        return jsonify({'status': 'ERROR', 'message': 'Job not found'}), 404
        
    if job['status'] != 'COMPLETED' or not job['output_filename']:
        return jsonify({'status': 'ERROR', 'message': 'Job results are not ready'}), 400
        
    network_id = job.get('network_id')
    
    # 1. Fetch nodes for this network
    nodes_list = []
    if db_available:
        try:
            db_nodes = list(nodes_collection.find({'network_id': network_id}))
            nodes_list = [serialize_node(n) for n in db_nodes]
        except Exception as e:
            print("Error fetching job nodes from MongoDB:", e)
    else:
        nodes_list = [n for n in in_memory_nodes if n.get('network_id') == network_id]
        
    # If no nodes saved, return empty
    if not nodes_list:
        return jsonify({'status': 'ERROR', 'message': 'Nodes not found for this network'}), 404
        
    output_path = os.path.join(OUTPUT_FOLDER, job['output_filename'])
    if not os.path.exists(output_path):
        return jsonify({'status': 'ERROR', 'message': 'Result Excel file not found'}), 404
        
    try:
        # 2. Parse Excel file for active routes and node metrics
        df_routes = pd.read_excel(output_path, 'Routes')
        df_nodes = pd.read_excel(output_path, 'Nodes')
        
        # Filter active routes
        df_active = df_routes[df_routes['Status'] == 'ACTIVE']
        
        routes = []
        for _, r in df_active.iterrows():
            routes.append({
                'id': str(r.get('Route ID', '')),
                'from_id': str(r.get('From Node ID', '')),
                'to_id': str(r.get('To Node ID', '')),
                'from_type': str(r.get('From Type', '')),
                'to_type': str(r.get('To Type', '')),
                'flow': float(r.get('Flow', 0.0)),
                'product_type': str(r.get('Product / Milk Type', '')),
                'unit': str(r.get('Unit', '')),
                'distance': float(r.get('Distance (km)', 0.0)),
                'cost': float(r.get('Transport Cost (₹)', 0.0)),
                'total_vehicles': int(r.get('Total Vehicles', 0)) if pd.notna(r.get('Total Vehicles')) else 0,
                'total_vehicle_capacity': float(r.get('Total Vehicle Capacity (L)', 0.0)) if pd.notna(r.get('Total Vehicle Capacity (L)')) else 0.0,
                'excess_vehicle_capacity': float(r.get('Excess Vehicle Capacity (L)', 0.0)) if pd.notna(r.get('Excess Vehicle Capacity (L)')) else 0.0
            })
            
        node_metrics = {}
        for _, row in df_nodes.iterrows():
            nid = str(row['Node ID'])
            inflow = float(row.get('Inflow Throughput', 0.0))
            outflow = float(row.get('Outflow Throughput', 0.0))
            if nid not in node_metrics:
                node_metrics[nid] = {'inflow': 0.0, 'outflow': 0.0}
            node_metrics[nid]['inflow'] += inflow
            node_metrics[nid]['outflow'] += outflow
            
        # Round node metrics
        for nid in node_metrics:
            node_metrics[nid]['inflow'] = round(node_metrics[nid]['inflow'], 2)
            node_metrics[nid]['outflow'] = round(node_metrics[nid]['outflow'], 2)
            
        # Read vehicle allocations from 'BMC Vehicle Allocation' sheet if it exists
        vehicle_allocations = []
        if 'BMC Vehicle Allocation' in pd.ExcelFile(output_path).sheet_names:
            df_veh = pd.read_excel(output_path, 'BMC Vehicle Allocation')
            for _, r in df_veh.iterrows():
                vehicle_allocations.append({
                    'bmc_id': str(r.get('BMC ID', '')),
                    'bmc_name': str(r.get('BMC Name', '')),
                    'plant_id': str(r.get('Plant ID', '')),
                    'plant_name': str(r.get('Plant Name', '')),
                    'product_type': str(r.get('Product / Milk Type', '')),
                    'flow': float(r.get('Flow Quantity', 0.0)) if pd.notna(r.get('Flow Quantity')) else 0.0,
                    'total_vehicles': int(r.get('Total Vehicles', 0)) if pd.notna(r.get('Total Vehicles')) else 0,
                    'total_vehicle_capacity': float(r.get('Total Vehicle Capacity (L)', 0.0)) if pd.notna(r.get('Total Vehicle Capacity (L)')) else 0.0,
                    'excess_vehicle_capacity': float(r.get('Excess Vehicle Capacity (L)', 0.0)) if pd.notna(r.get('Excess Vehicle Capacity (L)')) else 0.0,
                    'vehicle_reason': str(r.get('VehicleReason', 'Supplied')) if pd.notna(r.get('VehicleReason')) else 'Supplied',
                    'cluster': str(r.get('SupplierCluster', '')) if pd.notna(r.get('SupplierCluster')) else '',
                    'subcluster': str(r.get('SupplierSubCluster', '')) if pd.notna(r.get('SupplierSubCluster')) else '',
                    'leave_quantity': float(r.get('LeaveQuantity', 0.0)) if pd.notna(r.get('LeaveQuantity')) else 0.0
                })

        # Parse subcluster vehicle pools from the input spreadsheet
        vehicle_pools = {}
        input_path = os.path.join(UPLOAD_FOLDER, job['input_filename'])
        if os.path.exists(input_path):
            vehicle_limits_map = parse_bmc_vehicles(input_path)
            for bmc_id, info in vehicle_limits_map.items():
                if isinstance(info, dict) and 'limits' in info:
                    c = info.get('cluster', '')
                    sc = info.get('subcluster', '')
                    key = f"{c}||{sc}"
                    if key not in vehicle_pools:
                        vehicle_pools[key] = {
                        }
                    limits = info['limits']

        return jsonify({
            'status': 'SUCCESS',
            'job_id': job_id,
            'network_id': network_id,
            'nodes': nodes_list,
            'routes': routes,
            'node_metrics': node_metrics,
            'summary': job.get('result_summary', {}),
            'vehicle_allocations': vehicle_allocations,
            'vehicle_pools': vehicle_pools
        })
    except Exception as e:
        import traceback
        print("Error parsing Excel for details:", traceback.format_exc())
        return jsonify({'status': 'ERROR', 'message': f'Failed to parse Excel results: {str(e)}'}), 500


if __name__ == '__main__':
    # Running on port 5001 so it doesn't conflict with any running instance of the original app
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting SupplierNetworkMap on port {port}...")
    app.run(debug=True, use_reloader=False, port=port)
