import pandas as pd
import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime

def generate_supplier_list():
    # Load environment variables
    load_dotenv()
    
    # File paths
    input_file = r'D:\WRMSWork\Network-Planner-Api\NetworkSupplier\uploads\dairy_customers.xlsx'
    output_file = r'D:\WRMSWork\Network-Planner-Api\NetworkSupplier\uploads\supplier_list.xlsx'
    
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
            
        # Filter rows where TypeName is 'Supplier'
        supplier_df = df[df['TypeName'] == 'Supplier']
        
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mfimongomaster:mongomongo%26*(@localhost:27018/?authSource=admin')
        mongo_db_name = os.getenv('MONGO_DB', 'Network-Planner')
        
        print(f"Connecting to MongoDB at {mongo_uri} (Database: {mongo_db_name})...")
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]
        collection = db['SupplierMaster']
        
        # Drop previous collection to avoid duplicates
        collection.drop()
        
        records = []
        now = datetime.utcnow()
        seen_supplier_codes = set()
        
        for index, row in supplier_df.iterrows():
            supplier_code = str(row.get('code', '')).strip()
            if not supplier_code or supplier_code in seen_supplier_codes:
                continue
            seen_supplier_codes.add(supplier_code)
            
            # Map fields according to src/models/supplier.py
            record = {
                "SupplierCode": supplier_code,
                "SupplierName": str(row.get('name', '')),
                "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                "shortName": str(row.get('short_name', '')),
                "Description": None,
                "Vehicles": [],
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
            print(f"Successfully inserted {len(result.inserted_ids)} records into the SupplierMaster collection.")
            
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
    generate_supplier_list()
