import asyncio
import os
import time
import uuid
from datetime import datetime
import pandas as pd
import httpx
from dotenv import load_dotenv

load_dotenv()

from src.config.environment import Environment
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
    
    # Fetch master data to map codes to names
    api_dict = {}
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            r = client.get('https://apinode1.secutrak.in/mobileApiDairyM/getCustomerLocationMapping')
            m_data = r.json().get('data', [])
            api_dict = {str(d.get('code')): d.get('name', '') for d in m_data}
    except Exception as e:
        print(f"Error fetching location mapping in process_excel_and_save: {e}")
        # fallback to master_dict
        api_dict = {k: v.get('name', '') for k, v in master_dict.items()}

    try:
        output_path = os.path.join(optimizer_solver.OUTPUT_FOLDER, f"results_{request_id}.xlsx")
        if not os.path.exists(output_path):
            print(f"Optimizer output not found at {output_path}")
            return
            
        print(f"Reading optimizer output from {output_path}")
        xls = pd.ExcelFile(output_path)
        sheet_names = xls.sheet_names
        
        input_xls = pd.ExcelFile(excel_path)
        input_sheet_names = input_xls.sheet_names
        df_map = pd.read_excel(input_xls, 'Plant_BMC_Mapping')
        df_input_nodes = pd.read_excel(input_xls, 'Nodes') if 'Nodes' in input_sheet_names else pd.DataFrame()
        df_input_veh = pd.read_excel(input_xls, 'Vehicle Supplier Allocation') if 'Vehicle Supplier Allocation' in input_sheet_names else pd.DataFrame()
        input_xls.close()
        
        bmc_supp_map = dict(zip(df_map['BMCCode'].astype(str), df_map['Supplier']))
        bmc_supp_code_map = dict(zip(df_map['BMCCode'].astype(str), df_map['SupplierCode']))
        
        df_veh = pd.read_excel(xls, 'BMC Vehicle Allocation') if 'BMC Vehicle Allocation' in sheet_names else pd.DataFrame()
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
        if not df_input_nodes.empty:
            df_plants = df_input_nodes[df_input_nodes['type'] == 'plant']
            for _, r in df_plants.iterrows():
                p_code = str(r.get('node_id', ''))
                format_1.append({
                    "plantcode": p_code,
                    "plantname": api_dict.get(p_code, str(r.get('name', ''))),
                    "producttype": str(r.get('commodity', '')),
                    "supply": float(safe_val(r.get('demand', 0)))
                })
        result_doc['plantSupply'] = format_1
        
        # 2. suppliercode, suppliername, all product name key, Total Supply, BMC: [...]
        format_2 = []
        if not df_input_nodes.empty:
            df_hubs = df_input_nodes[df_input_nodes['type'] == 'hub'].copy()
            df_hubs['BMCCode'] = df_hubs['node_id'].astype(str)
            df_hubs['SupplierCode'] = df_hubs['BMCCode'].map(bmc_supp_code_map)
            df_hubs['SupplierName'] = df_hubs['BMCCode'].map(bmc_supp_map)
            
            grouped = df_hubs.groupby('SupplierCode')
            for supp_code, group in grouped:
                supp_name = api_dict.get(str(supp_code), group['SupplierName'].iloc[0] if not group.empty and 'SupplierName' in group else '')
                supp_data = {
                    "suppliercode": supp_code,
                    "suppliername": supp_name,
                    "FCM": 0.0, "MM": 0.0, "BM": 0.0, "CM": 0.0,
                    "BMC": []
                }
                
                for _, r in group.iterrows():
                    b_code_full = str(r.get('BMCCode', ''))
                    b_code = b_code_full.split('_')[-1] if '_' in b_code_full else b_code_full
                    prod = str(r.get('commodity', '')).upper()
                    cap = float(safe_val(r.get('capacity', 0)))
                    
                    fcm = cap if prod == 'FCM' else 0.0
                    mm = cap if prod == 'MM' else 0.0
                    bm = cap if prod == 'BM' else 0.0
                    cm = cap if prod == 'CM' else 0.0
                    
                    supp_data['FCM'] += fcm
                    supp_data['MM'] += mm
                    supp_data['BM'] += bm
                    supp_data['CM'] += cm
                    
                    supp_data['BMC'].append({
                        "BMCCode": b_code,
                        "BMCName": api_dict.get(b_code, str(r.get('name', ''))),
                        "FCM": fcm, "MM": mm, "BM": bm, "CM": cm,
                        "TotalSupply": fcm + mm + bm + cm
                    })
                supp_data['Total Supply'] = supp_data['FCM'] + supp_data['MM'] + supp_data['BM'] + supp_data['CM']
                format_2.append(supp_data)
        result_doc['supplierProductSupply'] = format_2
        
        # 3. suppliercode, suppliername, all vehicle name key
        format_3 = []
        if not df_input_veh.empty:
            grouped_veh = df_input_veh.groupby('SupplierCluster')
            for supp_code, group in grouped_veh:
                supp_name = api_dict.get(str(supp_code), "")
                veh_data = {"suppliercode": supp_code, "suppliername": supp_name}
                for col in group.columns:
                    if col.startswith('V') and len(col) == 3:
                        veh_data[col] = int(group[col].sum())
                format_3.append(veh_data)
        result_doc['supplierVehicles'] = format_3
        
        # 4, 5, 6, 7, 8 from 'Routes' or 'Hub To Plant'
        format_4 = []
        format_5 = []
        format_6 = []
        format_7 = []
        format_8 = []
        if not df_routes.empty:
            df_routes['From Node ID'] = df_routes['From Node ID'].astype(str)
            df_routes['To Node ID'] = df_routes['To Node ID'].astype(str)
            df_routes['SupplierCode'] = df_routes['From Node ID'].map(bmc_supp_code_map)
            df_routes['SupplierName'] = df_routes['From Node ID'].map(bmc_supp_map)
            
            def map_product(prod):
                prod_upper = str(prod).upper().strip()
                if prod_upper == 'BM TO FCM':
                    return 'FCM'
                elif prod_upper == 'FCM TO MM' or prod_upper == 'BM TO MM':
                    return 'MM'
                return prod
            df_routes['Product / Milk Type'] = df_routes['Product / Milk Type'].apply(map_product)
            
            # Format 4: Supplier, Plant, ProductType, sum of flow, sum of Distance, no of trips (basis of supplier, plant, product)
            g4 = df_routes.groupby(['SupplierCode', 'To Node ID', 'Product / Milk Type'])
            for (supp, plant, prod), group in g4:
                format_4.append({
                    "Supplier": supp, "SupplierName": api_dict.get(str(supp), ""),
                    "Plant": plant, "PlantName": api_dict.get(str(plant), ""),
                    "ProductType": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "Distance": float(group['Distance (km)'].sum()),
                    "Total Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0
                })

                
            # Format 5: Supplier, BMCCode, PlantCode, ProductType, flow, distance, trips
            g5 = df_routes.groupby(['SupplierCode', 'From Node ID', 'To Node ID', 'Product / Milk Type'])
            for (supp, bmc, plant, prod), group in g5:
                actual_bmc = str(bmc).split('_')[-1] if '_' in str(bmc) else str(bmc)
                format_5.append({
                    "Supplier": supp, "SupplierName": api_dict.get(str(supp), ""),
                    "BMCCode": actual_bmc, "BMCName": api_dict.get(actual_bmc, ""),
                    "PlantCode": plant, "PlantName": api_dict.get(str(plant), ""),
                    "ProductType": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "TotalDistance": float(group['Distance (km)'].sum()),
                    "Total Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0
                })
                
            # Format 6: Plant, BMCCode, all product name keys
            g6 = df_routes.groupby(['To Node ID', 'From Node ID'])
            for (plant, bmc), group in g6:
                actual_bmc = str(bmc).split('_')[-1] if '_' in str(bmc) else str(bmc)
                d6 = {
                    "Plant": plant, "PlantName": api_dict.get(str(plant), ""),
                    "BMCCode": actual_bmc, "BMCName": api_dict.get(actual_bmc, ""),
                    "FCM": 0, "MM": 0, "BM": 0, "CM": 0
                }
                for _, r in group.iterrows():
                    prod = str(r['Product / Milk Type']).upper()
                    if prod in d6:
                        d6[prod] += float(r.get('Dispatch Quantity', 0.0))
                format_6.append(d6)
                
            # Format 7: Plant, ProductType, Flow Quantity, TotalDistance, Total No.of Trips
            g7 = df_routes.groupby(['To Node ID', 'Product / Milk Type'])
            for (plant, prod), group in g7:
                format_7.append({
                    "Plant": plant, "PlantName": api_dict.get(str(plant), ""),
                    "ProductType": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "TotalDistance": float(group['Distance (km)'].sum()),
                    "Total No.of Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0
                })
                
            # Format 8: supplierCode, supplierName, ProductCode, Dispatch Quantity, V07...V35
            g8 = df_routes.groupby(['SupplierCode', 'Product / Milk Type'])
            for (supp_code, prod), group in g8:
                supp_name = api_dict.get(str(supp_code), group['SupplierName'].iloc[0] if 'SupplierName' in group and not group['SupplierName'].empty else '')
                row_data = {
                    "supplierCode": supp_code,
                    "supplierName": supp_name,
                    "ProductCode": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "V07": 0, "V10": 0, "V12": 0, "V15": 0, "V20": 0, "V25": 0, "V30": 0, "V35": 0
                }
                for col in group.columns:
                    if col.startswith('V') and 'Vehicles' in col:
                        veh_key = col.split(' ')[0]
                        if veh_key in row_data:
                            row_data[veh_key] = int(group[col].sum())
                format_8.append(row_data)

        result_doc['supplierPlantProduct'] = format_4
        result_doc['supplierBmcProduct'] = format_5
        result_doc['plantBmcProduct'] = format_6
        result_doc['plantProduct'] = format_7
        result_doc['supplierProductVehicles'] = format_8
        settings_repo = RequestSettingsRepository()
        setting_doc = await settings_repo.collection.find_one({"requestId": request_id})
        max_distance = setting_doc.get("maxDistance", 0) if setting_doc else 0
        result_doc['MAX_DISTANCE'] = max_distance
        
        try:
            report_path = os.path.join(optimizer_solver.OUTPUT_FOLDER, f"reports_{request_id}.xlsx")
            with pd.ExcelWriter(report_path) as writer:
                wrote_any = False
                for f_data, s_name in [
                    (format_1, 'plantSupply'), (format_2, 'supplierProductSupply'),
                    (format_3, 'supplierVehicles'), (format_4, 'supplierPlantProduct'),
                    (format_5, 'supplierBmcProduct'), (format_6, 'plantBmcProduct'),
                    (format_7, 'plantProduct'), (format_8, 'supplierProductVehicles'),
                    ([{"MAX_DISTANCE": max_distance}], 'MAX_DISTANCE')
                ]:
                    if f_data:
                        df_f = pd.DataFrame(f_data)
                        for col in df_f.columns:
                            if df_f[col].apply(lambda x: isinstance(x, (list, dict))).any():
                                df_f[col] = df_f[col].astype(str)
                        df_f.to_excel(writer, sheet_name=s_name, index=False)
                        wrote_any = True
                if not wrote_any:
                    pd.DataFrame([{"Message": "No data"}]).to_excel(writer, sheet_name='Empty', index=False)
            print(f"Saved reports Excel at {report_path}")
        except Exception as e:
            print(f"Error saving reports Excel: {e}")
        
        
        def sanitize_for_mongo(obj):
            if isinstance(obj, dict):
                return {str(k): sanitize_for_mongo(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_for_mongo(v) for v in obj]
            elif isinstance(obj, datetime):
                return obj
            elif hasattr(obj, 'item'):
                return obj.item()
            elif pd.api.types.is_scalar(obj) and pd.isna(obj):
                return None
            return obj
            
        result_doc = sanitize_for_mongo(result_doc)
        await results_repo.collection.insert_one(result_doc)
        print(f"Saved DB records for {request_id}")
        
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error parsing/saving results for {request_id}: {e}")

async def poll_requests():
    # Environment.JOB_ID check removed so that the task can start and pause dynamically
        
    await DatabaseConnection.connect()
    
    opt_repo = OptimizationRequestsRepository()
    plants_repo = RequestPlantsRepository()
    mmc_repo = RequestMMCsRepository()
    vehicles_repo = RequestVehiclesRepository()
    settings_repo = RequestSettingsRepository()
    mapping_repo = RequestPlantSupplierMappingRepository()
    
    print("Background worker started. Polling for pending requests...")
    is_paused = False
    
    while True:
        try:
            from dotenv import dotenv_values
            env_vars = dotenv_values(".env")
            job_val = env_vars.get("JOB", env_vars.get("job", "false"))
            if str(job_val).lower() != "true":
                if not is_paused:
                    print(f"Job disabled in .env (value={job_val}). Background worker paused.")
                    is_paused = True
                await asyncio.sleep(5)
                continue
                
            if is_paused:
                print("job=true detected in .env. Background worker resumed.")
                is_paused = False
            pending_req = await opt_repo.collection.find_one_and_update(
                {"status": "Pending"},
                {"$set": {"status": "InProgress", "startedOn": datetime.utcnow()}}
            )
            
            if not pending_req:
                await asyncio.sleep(5)
                continue
                
            request_id = pending_req["requestId"]
            network_id = str(uuid.uuid4())
            print(f"Processing Request: {request_id} with Network ID: {network_id}")
            
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
                    "price": 0, "network_id": network_id
                })
                
            for rm in req_mmcs:
                m_code = str(rm["mmcCode"])
                s_code = str(rm.get("supplierCode", ""))
                db_bmc = master_dict.get(m_code, {})
                lat = db_bmc.get("geocoord", "0.0,0.0").split(",")[0] if db_bmc.get("geocoord") else 0.0
                lng = db_bmc.get("geocoord", "0.0,0.0").split(",")[1] if db_bmc.get("geocoord") else 0.0
                name = db_bmc.get("name", m_code)
                
                hub_node_id = f"{s_code}_{m_code}" if s_code else m_code
                
                nodes.append({
                    "node_id": hub_node_id, "name": name, "type": "hub", "subtype": "",
                    "lat": float(lat), "lng": float(lng), "commodity": rm["productCode"],
                    "supply":0, "capacity": rm["availableSupply"],
                    "cost": 0, "yield": 0, "demand": 0, "price": 0, "network_id": network_id
                })
                
            df_nodes = pd.DataFrame(nodes) if nodes else pd.DataFrame(columns=["node_id", "name", "type", "subtype", "lat", "lng", "commodity", "supply", "capacity", "cost", "yield", "demand", "price", "network_id"])
            
            mapping_list = []
            dist_list = []
            
            valid_suppliers = set(m["supplierCode"] for m in req_mmcs)
            req_mappings = [m for m in req_mappings if m["supplierCode"] in valid_suppliers]
            
            import math
            for m in req_mappings:
                for mmc in req_mmcs:
                    if m["supplierCode"] == mmc["supplierCode"] and m["productCode"] == mmc["productCode"]:
                        p_code = str(m["plantCode"])
                        b_code = str(mmc["mmcCode"])
                        supplier_code = str(m["supplierCode"])
                        
                        plant_name = master_dict.get(p_code, {}).get('name', p_code)
                        bmc_name = master_dict.get(b_code, {}).get('name', b_code)
                        supp_name = master_dict.get(supplier_code, {}).get('name', supplier_code)
                        
                        bmc_node_id = f"{supplier_code}_{b_code}" if supplier_code else b_code
                        
                        mapping_list.append({
                            "PlantCode": p_code, "Plant": plant_name, "Supplier": supp_name, "SupplierCode": supplier_code,
                            "BMCCode": bmc_node_id, "BMC": bmc_name, "commodity": m["productCode"]
                        })
            
            unique_suppliers = list(set(m["supplierCode"] for m in req_mmcs))
            for s_code in unique_suppliers:
                supplier_plants = list(set(m["plantCode"] for m in req_mappings if m["supplierCode"] == s_code))
                supplier_bmcs = list(set(m["mmcCode"] for m in req_mmcs if m["supplierCode"] == s_code))
                supp_name = master_dict.get(s_code, {}).get('name', s_code)
                
                for b_code in supplier_bmcs:
                    for p_code in supplier_plants:
                        b_code_str = str(b_code)
                        p_code_str = str(p_code)
                        route = f"{b_code_str}-{p_code_str}"
                        dist = math.ceil(dist_dict.get(route, 0.0))
                        
                        bmc_node_id = f"{s_code}_{b_code_str}" if s_code else b_code_str
                        
                        dist_list.append({
                            "BMC Code": bmc_node_id, "Plant Code": p_code_str, "Distance": dist,
                            "Supplier": supp_name, "Supplier Code": str(s_code), "Remark": ""
                        })
                        
            df_mapping = pd.DataFrame(mapping_list).drop_duplicates() if mapping_list else pd.DataFrame(columns=["PlantCode", "Plant", "Supplier", "SupplierCode", "BMCCode", "BMC", "commodity"])
            df_distance = pd.DataFrame(dist_list).drop_duplicates() if dist_list else pd.DataFrame(columns=["BMC Code", "Plant Code", "Distance", "Supplier", "Supplier Code", "Remark"])
            
            import random
            if not df_distance.empty and (df_distance['Distance'] == 0.0).any():
                zero_dist_mask = df_distance['Distance'] == 0.0
                df_distance.loc[zero_dist_mask, 'Distance'] = [random.randint(50, 100) for _ in range(zero_dist_mask.sum())]
            
            if not df_distance.empty and (df_distance['Distance'] == 0.0).any():
                zero_dist_rows = df_distance[df_distance['Distance'] == 0.0]
                error_msg = f"Zero distance found for rows: {zero_dist_rows.to_dict('records')}"
                raise ValueError(error_msg)
            
            v_alloc_data = []
            supplier_codes = list(set([m["supplierCode"] for m in req_mmcs]))
            for s_code in supplier_codes:
                row = {
                    "SupplierCluster": s_code, "SupplierSubCluster": "SubCluster_01_A", "Strategy": "Least Vehicle Strategy",
                    "FlowLowMarginPercentage": 0, "FlowHighMarginPercentage": 0,
                    "V07": 0, "V10": 0, "V12": 0, "V15": 0, "V20": 0, "V25": 0, "V30": 0, "V35": 0
                }
                has_vehicles = False
                for v in req_vehicles:
                    if v["supplierCode"] == s_code:
                        has_vehicles = True
                        vt = v["vehicleType"].upper().replace(' ', '')
                        count = v.get("vehicleCount", 0)
                        if count == 0:
                            count = 1000
                        if vt in row:
                            row[vt] += count
                
                if not has_vehicles:
                    for vt in ["V07", "V10", "V12", "V15", "V20", "V25", "V30", "V35"]:
                        row[vt] = 1000
                        
                v_alloc_data.append(row)
            df_vehicle_alloc = pd.DataFrame(v_alloc_data)
            
            vehicle_capacity_map = {
                "V07": {"From": 3, "To": 7, "Name": "7L"},
                "V10": {"From": 8, "To": 11, "Name": "10L"},
                "V12": {"From": 11, "To": 12, "Name": "12L"},
                "V15": {"From": 14, "To": 16, "Name": "15L"},
                "V20": {"From": 19, "To": 22, "Name": "20L"},
                "V25": {"From": 23, "To": 26, "Name": "25L"},
                "V30": {"From": 27, "To": 32, "Name": "30L"},
                "V35": {"From": 33, "To": 40, "Name": "35L"},
            }
            vehicle_type_data = []
            for v in req_vehicles:
                vt = v["vehicleType"].upper().replace(' ', '')
                f_val = vehicle_capacity_map.get(vt, {}).get("From", 0)
                t_val = vehicle_capacity_map.get(vt, {}).get("To", 100)
                n_val = vehicle_capacity_map.get(vt, {}).get("Name", v["vehicleType"])
                vehicle_type_data.append({"Vehicle Name": n_val, "VehicleCode": v["vehicleType"], "From": f_val, "To": t_val})
            df_vehicle_type = pd.DataFrame(vehicle_type_data).drop_duplicates() if vehicle_type_data else pd.DataFrame()
            
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
            optimizer_solver.process_job_in_background(job_id=request_id, network_id=network_id, nodes=parsed_nodes, transport_cost_per_km=0.02, excel_file_path=excel_path)
            
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
                        {"$set": {"status": "Failed", "completedOn": datetime.utcnow(), "errorMessage": str(e)}}
                    )
            except:
                pass
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(poll_requests())
