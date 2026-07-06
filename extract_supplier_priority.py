import os
import httpx
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime

def generate_supplier_priority():
    # Load environment variables
    load_dotenv()
    
    url = "https://apinode1.secutrak.in/mobileApiDairyM/getSupplierPriority"
    headers = {
        "Authorization": "Bearer 40Y8h3xcr3nGBOQ154d154PH23mSj770"
    }
    files = {
        "AccessToken": (None, "40Y8h3xcr3nGBOQ154d154PH23mSj770")
    }
    
    print("Fetching data from API...")
    try:
        # Use httpx to make the post request synchronously
        with httpx.Client(follow_redirects=True) as api_client:
            response = api_client.post(url, headers=headers, files=files)
            
        if response.status_code != 200:
            print(f"Failed to fetch data from API. Status: {response.status_code}")
            return
            
        json_data = response.json()
        if json_data.get("Status") != "success":
            print(f"API returned error! Full response: {response.text}")
            return
            
        items = json_data.get("Data", [])
        print(f"Fetched {len(items)} items from API.")
        
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mfimongomaster:mongomongo%26*(@localhost:27018/?authSource=admin')
        mongo_db_name = os.getenv('MONGO_DB', 'Network-Planner')
        
        print(f"Connecting to MongoDB at {mongo_uri} (Database: {mongo_db_name})...")
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client[mongo_db_name]
        collection = db['SupplierPriorityMaster']
        
        # Drop previous collection to avoid duplicates
        collection.drop()
        
        records = []
        now = datetime.utcnow()
        seen_combinations = set()
        
        for item in items:
            plant_code = str(item.get('plant_code', '')).strip()
            supplier_code = str(item.get('supplier_code', '')).strip()
            
            combo = (plant_code, supplier_code)
            if not plant_code or not supplier_code or combo in seen_combinations:
                continue
            seen_combinations.add(combo)
            
            record = {
                "SupplierPriorityId": str(ObjectId()),
                "PlantCode": plant_code,
                "SupplierCode": supplier_code,
                "ProductCode": str(item.get('product_code', '')),
                "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                "IsActive": True,
                "CreatedBy": "system",
                "CreatedDate": now,
                "UpdatedBy": "system",
                "UpdatedDate": now
            }
            records.append(record)
            
        if records:
            result = collection.insert_many(records)
            print(f"Successfully inserted {len(result.inserted_ids)} records into the SupplierPriorityMaster collection.")
        else:
            print("No records to insert into MongoDB.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_supplier_priority()
