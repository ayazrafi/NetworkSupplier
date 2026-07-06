import pandas as pd
import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime

def generate_bmc_list():
    # Load environment variables
    load_dotenv()
    
    # File paths
    input_file = r'D:\WRMSWork\Network-Planner-Api\NetworkSupplier\uploads\dairy_customers.xlsx'
    output_file = r'D:\WRMSWork\Network-Planner-Api\NetworkSupplier\uploads\bmc_list.xlsx'
    
    if not os.path.exists(input_file):
        print(f"Error: Could not find {input_file}")
        return
        
    print(f"Reading {input_file}...")
    
    try:
        # Read the first sheet
        df = pd.read_excel(input_file, sheet_name=0)
        
        # Check if 'TypeName' column exists
        if 'TypeName' not in df.columns:
            print("Error: 'TypeName' column not found.")
            return
            
        # Filter rows where TypeName is 'MCC'
        bmc_df = df[df['TypeName'] == 'MCC']
        
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mfimongomaster:mongomongo%26*(@localhost:27018/?authSource=admin')
        mongo_db_name = os.getenv('MONGO_DB', 'Network-Planner')
        
        print(f"Connecting to MongoDB at {mongo_uri} (Database: {mongo_db_name})...")
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]
        collection = db['BMCMaster']
        
        # Drop previous collection to avoid duplicates (optional but good for clean state)
        collection.drop()
        
        records = []
        now = datetime.utcnow()
        seen_bmc_codes = set()
        
        for index, row in bmc_df.iterrows():
            bmc_code = str(row.get('code', '')).strip()
            if not bmc_code or bmc_code in seen_bmc_codes:
                continue
            seen_bmc_codes.add(bmc_code)
            
            # Parse latitude and longitude from geocoord
            geocoord = str(row.get('geocoord', ''))
            lat, lon = 0.0, 0.0
            if ',' in geocoord:
                try:
                    parts = geocoord.split(',')
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                except ValueError:
                    pass
            
            # Map fields according to src/models/bmc.py and add requested fields
            record = {
                "BMCCode": bmc_code,
                "BMCName": str(row.get('name', '')),
                "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                "Address": None,
                "Latitude": lat,
                "Longitude": lon,
                "ContactPerson": None,
                "MobileNumber": None,
                "IsActive": True,
                "CreatedBy": None,
                "CreatedDate": now,
                "UpdatedBy": None,
                "UpdatedDate": now
            }
            records.append(record)
            
        if records:
            # Insert into MongoDB
            result = collection.insert_many(records)
            print(f"Successfully inserted {len(result.inserted_ids)} records into the BMCMaster collection.")
            
            # Convert transformed records to a dataframe for the excel output too
            # pymongo adds _id in-place, so we remove it and stringify ObjectId
            export_records = []
            for r in records:
                r_copy = r.copy()
                if '_id' in r_copy:
                    del r_copy['_id']
                r_copy['WorkZoneId'] = str(r_copy['WorkZoneId'])
                export_records.append(r_copy)
                
            output_df = pd.DataFrame(export_records)
            output_df.to_excel(output_file, index=False)
            print(f"Saved formatted list to: {output_file}")
            
        else:
            print("No records to insert into MongoDB.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_bmc_list()
