import asyncio
import os
import time
from datetime import datetime
import pandas as pd
import httpx
from dotenv import load_dotenv

load_dotenv()

from src.config.db import DatabaseConnection
from src.repositories.request import (
    OptimizationRequestsRepository,
    RequestPlantsRepository,
    RequestMMCsRepository,
    RequestVehiclesRepository,
    RequestSettingsRepository,
    RequestPlantSupplierMappingRepository
)
from src.repositories.result import OptimizerRequestResultRepository

import optimizer_solver

def fetch_master_data():
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            r = client.get('https://apinode1.secutrak.in/mobileApiDairyM/getCustomerLocationMapping')
            return r.json().get('data', [])
    except Exception as e:
        print(f"Error fetching master data: {e}")
        return []

def fetch_distance_data():
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            r = client.post('https://apinode1.secutrak.in/mobileApiDairyM/getRoutesDistance', json={"AccessToken":"40Y8h3xcr3nGBOQ154d154PH23mSj770"})
            return r.json().get('data', [])
    except Exception as e:
        print(f"Error fetching distance data: {e}")
        return []

async def process_excel_and_save(request_id, excel_path, master_dict):
    results_repo = OptimizerRequestResultRepository()
    
    try:
        output_path = os.path.join(optimizer_solver.OUTPUT_FOLDER, f"results_{request_id}.xlsx")
        if not os.path.exists(output_path):
            print(f"Optimizer output not found at {output_path}")
            return
            
        print(f"Reading optimizer output from {output_path}")
        xls = pd.ExcelFile(output_path)
        sheet_names = xls.sheet_names
        
        input_xls = pd.ExcelFile(excel_path)
        df_map = pd.read_excel(input_xls, 'Plant_BMC_Mapping')
        input_xls.close()
        
        bmc_supp_map = dict(zip(df_map['BMCCode'].astype(str), df_map['Supplier']))
        bmc_supp_code_map = dict(zip(df_map['BMCCode'].astype(str), df_map['SupplierCode']))
        
        df_veh = pd.read_excel(xls, 'BMC Vehicle Allocation') if 'BMC Vehicle Allocation' in sheet_names else pd.DataFrame()
        df_nodes = pd.read_excel(xls, 'Nodes') if 'Nodes' in sheet_names else pd.DataFrame()
        df_bmc_supp = pd.read_excel(xls, 'BMC Supply Report') if 'BMC Supply Report' in sheet_names else pd.DataFrame()
        df_routes = pd.read_excel(xls, 'Hub To Plant') if 'Hub To Plant' in sheet_names else pd.DataFrame()
        xls.close()
        
        if not df_veh.empty:
            df_veh['Supplier'] = df_veh['BMC ID'].astype(str).map(bmc_supp_map)
            df_veh['Supplier Code'] = df_veh['BMC ID'].astype(str).map(bmc_supp_code_map)
            
            with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_veh.to_excel(writer, sheet_name='BMC Vehicle Allocation', index=False)
            
        # Parse data formats
        result_doc = {"jobId": request_id, "createdAt": datetime.utcnow()}
        
        def safe_val(v):
            return 0 if pd.isna(v) else v
            
        # 1. plantcode, plantname, producttype, supply
        format_1 = []
        if not df_nodes.empty:
            df_plants = df_nodes[df_nodes['Type'] == 'plant']
            for _, r in df_plants.iterrows():
                format_1.append({
                    "plantcode": str(r.get('Node ID', '')),
                    "plantname": str(r.get('Name', '')),
                    "producttype": str(r.get('Commodity', '')),
                    "supply": float(safe_val(r.get('Inflow Throughput', 0)))
                })
        result_doc['plantSupply'] = format_1
        
        # 2. suppliercode, suppliername, all product name key, Total Supply, BMC: [...]
        format_2 = []
        if not df_bmc_supp.empty:
            df_bmc_supp['BMC ID'] = df_bmc_supp['BMC ID'].astype(str)
            df_bmc_supp['SupplierCode'] = df_bmc_supp['BMC ID'].map(bmc_supp_code_map)
            df_bmc_supp['SupplierName'] = df_bmc_supp['BMC ID'].map(bmc_supp_map)
            
            grouped = df_bmc_supp.groupby('SupplierCode')
            for supp_code, group in grouped:
                supp_name = group['SupplierName'].iloc[0]
                supp_data = {
                    "suppliercode": supp_code,
                    "suppliername": supp_name,
                    "FCM": float(group.get('Final FCM Supply', group.get('FCM {Supply}', pd.Series([0]))).sum()),
                    "MM": float(group.get('Final MM Supply', group.get('MM {Supply}', pd.Series([0]))).sum()),
                    "BM": float(group.get('BM {Supply}', pd.Series([0])).sum()),
                    "CM": float(group.get('CM {Supply}', pd.Series([0])).sum()),
                    "BMC": []
                }
                supp_data['Total Supply'] = supp_data['FCM'] + supp_data['MM'] + supp_data['BM'] + supp_data['CM']
                
                for _, r in group.iterrows():
                    fcm = float(safe_val(r.get('Final FCM Supply', r.get('FCM {Supply}', 0))))
                    mm = float(safe_val(r.get('Final MM Supply', r.get('MM {Supply}', 0))))
                    bm = float(safe_val(r.get('BM {Supply}', 0)))
                    cm = float(safe_val(r.get('CM {Supply}', 0)))
                    supp_data['BMC'].append({
                        "BMCCode": str(r.get('BMC ID', '')),
                        "BMCName": str(r.get('BMC Name', '')),
                        "FCM": fcm, "MM": mm, "BM": bm, "CM": cm,
                        "TotalSupply": fcm + mm + bm + cm
                    })
                format_2.append(supp_data)
        result_doc['supplierProductSupply'] = format_2
        
        # 3. suppliercode, suppliername, all vehicle name key
        format_3 = []
        if not df_veh.empty:
            grouped_veh = df_veh.groupby('Supplier Code')
            for supp_code, group in grouped_veh:
                supp_name = group['Supplier'].iloc[0] if 'Supplier' in group else ''
                veh_data = {"suppliercode": supp_code, "suppliername": supp_name}
                for col in group.columns:
                    if col.startswith('V') and 'Vehicles' in col:
                        veh_key = col.split(' ')[0]
                        veh_data[veh_key] = int(group[col].sum())
                format_3.append(veh_data)
        result_doc['supplierVehicles'] = format_3
        
        # 4, 5, 6, 7 from 'Routes' or 'Hub To Plant'
        format_4 = []
        format_5 = []
        format_6 = []
        format_7 = []
        if not df_routes.empty:
            df_routes['From Node ID'] = df_routes['From Node ID'].astype(str)
            df_routes['To Node ID'] = df_routes['To Node ID'].astype(str)
            df_routes['SupplierCode'] = df_routes['From Node ID'].map(bmc_supp_code_map)
            df_routes['SupplierName'] = df_routes['From Node ID'].map(bmc_supp_map)
            
            # Format 4: Supplier, Plant, ProductType, sum of flow, sum of Distance, no of trips (basis of supplier, plant, product)
            g4 = df_routes.groupby(['SupplierCode', 'To Node ID', 'Product / Milk Type'])
            for (supp, plant, prod), group in g4:
                format_4.append({
                    "Supplier": supp, "Plant": plant, "ProductType": prod,
                    "Flow Quantity": float(group['Flow'].sum()),
                    "Distance": float(group['Distance (km)'].sum()),
                    "Total Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0
                })
                
            # Format 5: Supplier, BMCCode, ProductType, flow, distance, trips (basis of BMCCode, ProductType)
            g5 = df_routes.groupby(['SupplierCode', 'From Node ID', 'Product / Milk Type'])
            for (supp, bmc, prod), group in g5:
                format_5.append({
                    "Supplier": supp, "BMCCode": bmc, "ProductType": prod,
                    "Flow Quantity": float(group['Flow'].sum()),
                    "TotalDistance": float(group['Distance (km)'].sum()),
                    "Total Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0
                })
                
            # Format 6: Plant, BMCCode, all product name keys
            g6 = df_routes.groupby(['To Node ID', 'From Node ID'])
            for (plant, bmc), group in g6:
                d6 = {"Plant": plant, "BMCCode": bmc, "FCM": 0, "MM": 0, "BM": 0, "CM": 0}
                for _, r in group.iterrows():
                    prod = str(r['Product / Milk Type']).upper()
                    if prod in d6:
                        d6[prod] += float(r['Flow'])
                format_6.append(d6)
                
            # Format 7: Plant, ProductType, Flow Quantity, TotalDistance, Total No.of Trips
            g7 = df_routes.groupby(['To Node ID', 'Product / Milk Type'])
            for (plant, prod), group in g7:
                format_7.append({
                    "Plant": plant, "ProductType": prod,
                    "Flow Quantity": float(group['Flow'].sum()),
                    "TotalDistance": float(group['Distance (km)'].sum()),
                    "Total No.of Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0
                })
                
        result_doc['supplierPlantProduct'] = format_4
        result_doc['supplierBmcProduct'] = format_5
        result_doc['plantBmcProduct'] = format_6
        result_doc['plantProduct'] = format_7
        
        await results_repo.collection.insert_one(result_doc)
        print(f"Saved DB records for {request_id}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error parsing/saving results for {request_id}: {e}")

async def poll_requests():
    await DatabaseConnection.connect()
    
    opt_repo = OptimizationRequestsRepository()
    plants_repo = RequestPlantsRepository()
    mmc_repo = RequestMMCsRepository()
    vehicles_repo = RequestVehiclesRepository()
    settings_repo = RequestSettingsRepository()
    mapping_repo = RequestPlantSupplierMappingRepository()
    
    print("Background worker started. Polling for pending requests...")
    
    while True:
        try:
            pending_req = await opt_repo.collection.find_one_and_update(
                {"status": "Pending"},
                {"$set": {"status": "InProgress", "startedOn": datetime.utcnow()}}
            )
            
            if not pending_req:
                await asyncio.sleep(5)
                continue
                
            request_id = pending_req["requestId"]
            print(f"Processing Request: {request_id}")
            
            req_plants = await plants_repo.collection.find({"requestId": request_id}).to_list(length=None)
            req_mmcs = await mmc_repo.collection.find({"requestId": request_id}).to_list(length=None)
            req_vehicles = await vehicles_repo.collection.find({"requestId": request_id}).to_list(length=None)
            req_mappings = await mapping_repo.collection.find({"requestId": request_id}).to_list(length=None)
            
            master_data = fetch_master_data()
            master_dict = {str(d.get('code')): d for d in master_data}
            
            distances_data = fetch_distance_data()
            dist_dict = {str(d.get('route_code')): float(d.get('distance', 0)) for d in distances_data}
            
            nodes = []
            for rp in req_plants:
                p_code = str(rp["plantCode"])
                db_plant = master_dict.get(p_code, {})
                lat = db_plant.get("geocoord", "0.0,0.0").split(",")[0] if db_plant.get("geocoord") else 0.0
                lng = db_plant.get("geocoord", "0.0,0.0").split(",")[1] if db_plant.get("geocoord") else 0.0
                name = db_plant.get("name", p_code)
                
                nodes.append({
                    "node_id": p_code, "name": name, "type": "plant", "subtype": "",
                    "lat": float(lat), "lng": float(lng), "commodity": rp["productCode"],
                    "supply": 0, "capacity": 0, "cost": 0, "yield": 0, "demand": rp["demand"],
                    "price": 0, "network_id": ""
                })
                
            for rm in req_mmcs:
                m_code = str(rm["mmcCode"])
                db_bmc = master_dict.get(m_code, {})
                lat = db_bmc.get("geocoord", "0.0,0.0").split(",")[0] if db_bmc.get("geocoord") else 0.0
                lng = db_bmc.get("geocoord", "0.0,0.0").split(",")[1] if db_bmc.get("geocoord") else 0.0
                name = db_bmc.get("name", m_code)
                
                nodes.append({
                    "node_id": m_code, "name": name, "type": "hub", "subtype": "",
                    "lat": float(lat), "lng": float(lng), "commodity": rm["productCode"],
                    "supply": rm["availableSupply"], "capacity": rm["availableSupply"],
                    "cost": 0, "yield": 100, "demand": 0, "price": 0, "network_id": ""
                })
                
            df_nodes = pd.DataFrame(nodes) if nodes else pd.DataFrame(columns=["node_id", "name", "type", "subtype", "lat", "lng", "commodity", "supply", "capacity", "cost", "yield", "demand", "price", "network_id"])
            
            mapping_list = []
            dist_list = []
            
            for m in req_mappings:
                for mmc in req_mmcs:
                    if m["supplierCode"] == mmc["supplierCode"] and m["productCode"] == mmc["productCode"]:
                        p_code = str(m["plantCode"])
                        b_code = str(mmc["mmcCode"])
                        supplier_code = str(m["supplierCode"])
                        
                        plant_name = master_dict.get(p_code, {}).get('name', p_code)
                        bmc_name = master_dict.get(b_code, {}).get('name', b_code)
                        supp_name = master_dict.get(supplier_code, {}).get('name', supplier_code)
                        
                        mapping_list.append({
                            "PlantCode": p_code, "Plant": plant_name, "Supplier": supp_name, "SupplierCode": supplier_code,
                            "BMCCode": b_code, "BMC": bmc_name, "commodity": m["productCode"]
                        })
                        
                        route = f"{b_code}-{p_code}"
                        dist = dist_dict.get(route, 0.0)
                        dist_list.append({
                            "BMC Code": b_code, "Plant Code": p_code, "Distance": dist,
                            "Supplier": supp_name, "Supplier Code": supplier_code, "Remark": ""
                        })
                        
            df_mapping = pd.DataFrame(mapping_list).drop_duplicates() if mapping_list else pd.DataFrame(columns=["PlantCode", "Plant", "Supplier", "SupplierCode", "BMCCode", "BMC", "commodity"])
            df_distance = pd.DataFrame(dist_list).drop_duplicates() if dist_list else pd.DataFrame(columns=["BMC Code", "Plant Code", "Distance", "Supplier", "Supplier Code", "Remark"])
            
            v_alloc_data = []
            supplier_codes = list(set([m["supplierCode"] for m in req_mappings]))
            for s_code in supplier_codes:
                row = {
                    "SupplierCluster": s_code, "SupplierSubCluster": "", "Strategy": "",
                    "FlowLowMarginPercentage": 0, "FlowHighMarginPercentage": 0,
                    "V07": 0, "V10": 0, "V12": 0, "V15": 0, "V20": 0, "V25": 0, "V30": 0, "V35": 0
                }
                for v in req_vehicles:
                    if v["supplierCode"] == s_code:
                        vt = v["vehicleType"].upper().replace(' ', '')
                        if vt in row:
                            row[vt] += v["vehicleCount"]
                v_alloc_data.append(row)
            df_vehicle_alloc = pd.DataFrame(v_alloc_data)
            
            df_vehicle_type = pd.DataFrame([{"Vehicle Name": v["vehicleType"], "VehicleCode": v["vehicleType"], "From": 0, "To": 100} for v in req_vehicles]).drop_duplicates() if req_vehicles else pd.DataFrame()
            
            output_dir = "uploads"
            os.makedirs(output_dir, exist_ok=True)
            excel_path = os.path.join(output_dir, f"request_{request_id}.xlsx")
            
            with pd.ExcelWriter(excel_path) as writer:
                df_nodes.to_excel(writer, sheet_name="Nodes", index=False)
                df_distance.to_excel(writer, sheet_name="Distance", index=False)
                df_mapping.to_excel(writer, sheet_name="Plant_BMC_Mapping", index=False)
                df_vehicle_alloc.to_excel(writer, sheet_name="Vehicle Supplier Allocation", index=False)
                df_vehicle_type.to_excel(writer, sheet_name="Vehicle Type", index=False)
                
            parsed_nodes = optimizer_solver.parse_excel_nodes(excel_path)
            # Use process_job_in_background which writes the result data
            optimizer_solver.process_job_in_background(job_id=request_id, network_id='', nodes=parsed_nodes, transport_cost_per_km=0.02, excel_file_path=excel_path)
            
            await process_excel_and_save(request_id, excel_path, master_dict)
            
            await opt_repo.collection.update_one(
                {"requestId": request_id},
                {"$set": {"status": "Completed", "completedOn": datetime.utcnow()}}
            )
            print(f"Request {request_id} processed successfully.")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error processing loop: {e}")
            try:
                if 'request_id' in locals():
                    await opt_repo.collection.update_one(
                        {"requestId": request_id},
                        {"$set": {"status": "Failed", "completedOn": datetime.utcnow()}}
                    )
            except:
                pass
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(poll_requests())
