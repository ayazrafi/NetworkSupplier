import pandas as pd
import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime

def generate_bmc_supplier_mapping():
    # Load environment variables
    load_dotenv()
    
    # File paths
    csv_file = r'D:\WRMSWork\Network-Planner-Api\NetworkSupplier\uploads\dairy_mcc_supplier_mapping_20260703.csv'
    excel_file = r'D:\WRMSWork\Network-Planner-Api\NetworkSupplier\uploads\dairy_customers.xlsx'
    
    if not os.path.exists(csv_file):
        print(f"Error: Could not find {csv_file}")
        return
        
    if not os.path.exists(excel_file):
        print(f"Error: Could not find {excel_file}")
        return
        
    try:
        # 1. Connect to MongoDB and fetch unique SupplierCodes from SupplierPriorityMaster
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mfimongomaster:mongomongo%26*(@localhost:27018/?authSource=admin')
        mongo_db_name = os.getenv('MONGO_DB', 'Network-Planner')
        
        print(f"Connecting to MongoDB at {mongo_uri} (Database: {mongo_db_name})...")
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]
        
        # Get unique suppliers
        supplier_priority_coll = db['SupplierPriorityMaster']
        unique_suppliers = supplier_priority_coll.distinct("SupplierCode")
        print(f"Found {len(unique_suppliers)} unique SupplierCodes in SupplierPriorityMaster.")
        
        if not unique_suppliers:
            print("No suppliers found in SupplierPriorityMaster. Exiting.")
            return

        # 2. Read CSV and filter based on SupplierCodes
        print(f"Reading {csv_file}...")
        mapping_df = pd.read_csv(csv_file)
        
        # Filter where 'code' matches SupplierCodes
        # Using astype(str) to ensure matching works properly
        mapping_df['code'] = mapping_df['code'].astype(str)
        unique_suppliers_str = [str(s) for s in unique_suppliers]
        
        matched_mappings = mapping_df[mapping_df['code'].isin(unique_suppliers_str)]
        mcc_ids = matched_mappings['mcc_id'].dropna().unique()
        print(f"Found {len(mcc_ids)} unique mcc_ids matching the suppliers.")
        
        if len(mcc_ids) == 0:
            print("No matching mcc_ids found. Exiting.")
            return

        # 3. Read Excel and filter based on mcc_ids
        print(f"Reading {excel_file}...")
        customers_df = pd.read_excel(excel_file, sheet_name=0)
        
        # Filter where 'id' matches mcc_ids
        matched_customers = customers_df[customers_df['id'].isin(mcc_ids)]
        
        # Construct the final records list
        records = []
        now = datetime.utcnow()
        seen_combinations = set()
        
        # Iterate over the mappings we found to construct the relationship
        for index, row in matched_mappings.iterrows():
            mcc_id = row['mcc_id']
            supplier_code = str(row['code']).strip()
            
            # Find the corresponding customer(BMC) record
            customer_match = matched_customers[matched_customers['id'] == mcc_id]
            
            if not customer_match.empty:
                # We can have multiple matches if the same mcc_id is present multiple times, but let's take the first
                bmc_code = str(customer_match.iloc[0]['code']).strip()
                
                combo = (bmc_code, supplier_code)
                if not bmc_code or not supplier_code or combo in seen_combinations:
                    continue
                seen_combinations.add(combo)
                
                record = {
                    "BMCCode": bmc_code,
                    "SupplierCode": supplier_code,
                    "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                    "IsActive": True,
                    "CreatedBy": "system",
                    "CreatedDate": now,
                    "UpdatedBy": "system",
                    "UpdatedDate": now
                }
                records.append(record)

        # 4. Save mapping to BMCSupplierMapping collection
        if records:
            mapping_coll = db['BMCSupplierMapping']
            mapping_coll.drop() # Clear previous data
            
            result = mapping_coll.insert_many(records)
            print(f"Successfully inserted {len(result.inserted_ids)} records into BMCSupplierMapping collection.")
        else:
            print("No mappings found to insert.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_bmc_supplier_mapping()
