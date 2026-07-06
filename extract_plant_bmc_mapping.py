import os
import math
import time
import httpx
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance in kilometers between two points on the earth."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    R = 6371.0  # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_google_maps_distances(api_key, origin, destinations):
    origin_str = f"{origin[0]},{origin[1]}"
    dest_str = "|".join([f"{d[0]},{d[1]}" for d in destinations])
    
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin_str,
        "destinations": dest_str,
        "key": api_key
    }
    
    with httpx.Client() as client:
        response = client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()

def generate_plant_bmc_mapping():
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mfimongomaster:mongomongo%26*(@localhost:27018/?authSource=admin')
        mongo_db_name = os.getenv('MONGO_DB', 'Network-Planner')
        
        print(f"Connecting to MongoDB at {mongo_uri} (Database: {mongo_db_name})...")
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]
        
        # Collections
        supplier_priority_coll = db['SupplierPriorityMaster']
        bmc_supplier_coll = db['BMCSupplierMapping']
        plant_coll = db['PlantMaster']
        bmc_coll = db['BMCMaster']
        plant_bmc_coll = db['PlantBMCDistanceMapping']
        
        # 1. Load Plant Coordinates
        print("Loading Plant Coordinates...")
        plant_coords = {}
        for p in plant_coll.find({}):
            code = p.get("PlantCode")
            lat, lon = p.get("Latitude"), p.get("Longitude")
            if code and lat is not None and lon is not None:
                plant_coords[code] = (lat, lon)
                
        # 2. Load BMC Coordinates
        print("Loading BMC Coordinates...")
        bmc_coords = {}
        for b in bmc_coll.find({}):
            code = b.get("BMCCode")
            lat, lon = b.get("Latitude"), b.get("Longitude")
            if code and lat is not None and lon is not None:
                bmc_coords[code] = (lat, lon)
        
        # 3. Fetch mappings to get valid combinations
        supplier_priorities = list(supplier_priority_coll.find({}))
        supplier_to_plants = defaultdict(set)
        for sp in supplier_priorities:
            if sp.get("SupplierCode") and sp.get("PlantCode"):
                supplier_to_plants[sp["SupplierCode"]].add(sp["PlantCode"])
                
        bmc_mappings = list(bmc_supplier_coll.find({}))
        supplier_to_bmcs = defaultdict(set)
        for bm in bmc_mappings:
            if bm.get("SupplierCode") and bm.get("BMCCode"):
                supplier_to_bmcs[bm["SupplierCode"]].add(bm["BMCCode"])
                
        # Get all unique plants and bmcs across all suppliers
        all_plants = set(p for plants in supplier_to_plants.values() for p in plants)
        all_bmcs = set(b for bmcs in supplier_to_bmcs.values() for b in bmcs)
        
        # Filter to those with valid coordinates
        all_plants = [p for p in all_plants if p in plant_coords]
        all_bmcs = [b for b in all_bmcs if b in bmc_coords]
        
        print(f"Valid unique plants: {len(all_plants)}, Valid unique BMCs: {len(all_bmcs)}")
        
        records = []
        now = datetime.utcnow()
        
        # 4. Generate records and calculate distances
        if not api_key:
            print("No GOOGLE_MAPS_API_KEY found. Using Haversine fallback.")
            for plant_code in all_plants:
                p_coord = plant_coords[plant_code]
                for bmc_code in all_bmcs:
                    b_coord = bmc_coords[bmc_code]
                    dist_km = haversine(p_coord[0], p_coord[1], b_coord[0], b_coord[1])
                    
                    # Assuming average speed of 40 km/h for travel time fallback
                    travel_time_min = (dist_km / 40.0) * 60.0
                    
                    records.append({
                        "PlantBMCDistanceMappingId": str(ObjectId()),
                        "PlantCode": plant_code,
                        "BMCCode": bmc_code,
                        "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                        "Distance": round(dist_km, 2),
                        "TravelTime": round(travel_time_min, 2),
                        "IsActive": True,
                        "CreatedBy": "system",
                        "CreatedDate": now,
                        "UpdatedBy": "system",
                        "UpdatedDate": now
                    })
        else:
            print("Using Google Maps Distance Matrix API. Processing in batches...")
            # Google Maps allows max 25 destinations per request when 1 origin is used.
            BATCH_SIZE = 25
            
            for plant_code in all_plants:
                p_coord = plant_coords[plant_code]
                
                # Chunk the BMCs
                for i in range(0, len(all_bmcs), BATCH_SIZE):
                    bmc_batch = all_bmcs[i:i + BATCH_SIZE]
                    dest_coords = [bmc_coords[b] for b in bmc_batch]
                    
                    try:
                        result = get_google_maps_distances(api_key, p_coord, dest_coords)
                        
                        if result.get("status") == "OK":
                            elements = result["rows"][0]["elements"]
                            for j, element in enumerate(elements):
                                bmc_code = bmc_batch[j]
                                b_coord = bmc_coords[bmc_code]
                                
                                dist_km = 0.0
                                travel_time_min = 0.0
                                
                                if element.get("status") == "OK":
                                    dist_meters = element["distance"]["value"]
                                    dist_km = dist_meters / 1000.0
                                    
                                    time_seconds = element["duration"]["value"]
                                    travel_time_min = time_seconds / 60.0
                                else:
                                    # Fallback to Haversine if specific route fails
                                    dist_km = haversine(p_coord[0], p_coord[1], b_coord[0], b_coord[1])
                                    travel_time_min = (dist_km / 40.0) * 60.0
                                    
                                records.append({
                                    "PlantBMCDistanceMappingId": str(ObjectId()),
                                    "PlantCode": plant_code,
                                    "BMCCode": bmc_code,
                                    "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                                    "Distance": round(dist_km, 2),
                                    "TravelTime": round(travel_time_min, 2),
                                    "IsActive": True,
                                    "CreatedBy": "system",
                                    "CreatedDate": now,
                                    "UpdatedBy": "system",
                                    "UpdatedDate": now
                                })
                        else:
                            print(f"API Error: {result.get('status')}")
                            # Fallback batch
                            for bmc_code in bmc_batch:
                                b_coord = bmc_coords[bmc_code]
                                dist_km = haversine(p_coord[0], p_coord[1], b_coord[0], b_coord[1])
                                travel_time_min = (dist_km / 40.0) * 60.0
                                records.append({
                                    "PlantBMCDistanceMappingId": str(ObjectId()),
                                    "PlantCode": plant_code,
                                    "BMCCode": bmc_code,
                                    "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                                    "Distance": round(dist_km, 2),
                                    "TravelTime": round(travel_time_min, 2),
                                    "IsActive": True,
                                    "CreatedBy": "system",
                                    "CreatedDate": now,
                                    "UpdatedBy": "system",
                                    "UpdatedDate": now
                                })
                                
                    except Exception as e:
                        print(f"Error fetching distance for plant {plant_code} batch {i}: {e}")
                        # Fallback batch
                        for bmc_code in bmc_batch:
                            b_coord = bmc_coords[bmc_code]
                            dist_km = haversine(p_coord[0], p_coord[1], b_coord[0], b_coord[1])
                            travel_time_min = (dist_km / 40.0) * 60.0
                            records.append({
                                "PlantBMCDistanceMappingId": str(ObjectId()),
                                "PlantCode": plant_code,
                                "BMCCode": bmc_code,
                                "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                                "Distance": round(dist_km, 2),
                                "TravelTime": round(travel_time_min, 2),
                                "IsActive": True,
                                "CreatedBy": "system",
                                "CreatedDate": now,
                                "UpdatedBy": "system",
                                "UpdatedDate": now
                            })
                    
                    # Sleep slightly to avoid hitting query limits if API is fast
                    time.sleep(0.5)

        # 5. Save mapping to PlantBMCDistanceMapping collection
        if records:
            plant_bmc_coll.drop() # Clear previous data
            result = plant_bmc_coll.insert_many(records)
            print(f"Successfully inserted {len(result.inserted_ids)} unique records into PlantBMCDistanceMapping collection.")
        else:
            print("No valid Plant-BMC mappings found to insert.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_plant_bmc_mapping()
