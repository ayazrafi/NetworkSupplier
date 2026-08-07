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
    RequestPlantSupplierMappingRepository,
    RequestConstraintsRepository,
    RequestProductConfigurationsRepository
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

def fetch_supplier_milk_summary(job_id):
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            r = client.post('https://apinode1.secutrak.in/mobileApiDairyM/getSupplierMilkSummary', json={"AccessToken":"40Y8h3xcr3nGBOQ154d154PH23mSj770", "jobId": job_id})
            return r.json().get('data', [])
    except Exception as e:
        print(f"Error fetching supplier milk summary: {e}")
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
        df_milk_config = pd.read_excel(input_xls, 'MilkConfig') if 'MilkConfig' in input_sheet_names else pd.DataFrame()
        df_milk_sub = pd.read_excel(input_xls, 'MilkSubstitution') if 'MilkSubstitution' in input_sheet_names else pd.DataFrame()
        input_xls.close()

        # Dynamically determine available milk types from MilkConfig and Nodes sheets
        dynamic_milk_types = []
        if not df_milk_config.empty and 'MilkType' in df_milk_config.columns:
            for m in df_milk_config['MilkType'].dropna().unique():
                m_str = str(m).strip().upper()
                if m_str and m_str not in dynamic_milk_types:
                    dynamic_milk_types.append(m_str)
        if not df_input_nodes.empty and 'commodity' in df_input_nodes.columns:
            for m in df_input_nodes['commodity'].dropna().unique():
                m_str = str(m).strip().upper()
                if m_str and m_str != 'NAN' and m_str not in dynamic_milk_types:
                    dynamic_milk_types.append(m_str)
        if not dynamic_milk_types:
            dynamic_milk_types = ['FCM', 'MM', 'BM', 'CM']
        
        supp_col = df_map['Supplier'] if 'Supplier' in df_map.columns else pd.Series(dtype=str)
        supp_code_col = df_map['SupplierCode'] if 'SupplierCode' in df_map.columns else supp_col
        bmc_supp_map = dict(zip(df_map['BMCCode'].astype(str), supp_col))
        bmc_supp_code_map = dict(zip(df_map['BMCCode'].astype(str), supp_code_col))
        
        veh_sheet = 'BMC Vehicle Allocation (Max Uti ' if 'BMC Vehicle Allocation (Max Uti ' in sheet_names else ('BMC Vehicle Allocation (Max Uti' if 'BMC Vehicle Allocation (Max Uti' in sheet_names else 'BMC Vehicle Allocation (Max Util)')
        df_veh = pd.read_excel(xls, veh_sheet) if veh_sheet in sheet_names else pd.DataFrame()
        
        if 'Routes (Max Utilized)' in sheet_names:
            df_routes = pd.read_excel(xls, 'Routes (Max Utilized)')
            if 'Status' in df_routes.columns:
                df_routes = df_routes[df_routes['Status'].astype(str).str.upper() == 'ACTIVE'].copy()
        else:
            df_routes = pd.DataFrame()
            
        if 'Total Supply (Max Util)' in sheet_names:
            df_total_supply = pd.read_excel(xls, 'Total Supply (Max Util)')
            if 'Status' in df_total_supply.columns:
                df_total_supply = df_total_supply[df_total_supply['Status'].astype(str).str.upper() == 'ACTIVE'].copy()
        else:
            df_total_supply = pd.DataFrame()
        xls.close()
        
        if not df_veh.empty:
            df_veh['Supplier'] = df_veh['BMC ID'].astype(str).map(bmc_supp_map)
            df_veh['Supplier Code'] = df_veh['BMC ID'].astype(str).map(bmc_supp_code_map)
            
            with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_veh.to_excel(writer, sheet_name=veh_sheet, index=False)
            
        # Parse data formats
        result_doc = {"jobId": request_id, "createdAt": datetime.utcnow()}
        
        # Helper to normalize codes (e.g., handles float values like '101.0' -> '101' and whitespace)
        def norm_code(val):
            if val is None or pd.isna(val):
                return ""
            s = str(val).strip()
            if s.endswith(".0"):
                s = s[:-2]
            return s

        # Fetch request constraints
        constraints_repo = RequestConstraintsRepository()
        req_constraints = await constraints_repo.collection.find({"requestId": request_id}).to_list(length=None)
        constraints_map = {str(c.get("supplierCode", "")).strip(): c for c in req_constraints}

        # Fetch supplier milk summary data
        milk_summary_data = fetch_supplier_milk_summary(request_id)
        print(f"[milk_summary] Received {len(milk_summary_data)} summary records from API for jobId={request_id}")
        
        # Aggregate milk summary data by (supplier_code, plant_code, milk_type), by BMC, and by Plant-Product
        milk_summary_agg = {}
        bmc_milk_summary_agg = {}
        plant_milk_summary_agg = {}
        for row in milk_summary_data:
            s_code = norm_code(row.get('supplier_code', row.get('supplierCode', row.get('SupplierCode'))))
            p_code = norm_code(row.get('plant_code', row.get('plantCode', row.get('PlantCode'))))
            m_type = norm_code(row.get('milk_type', row.get('milkType', row.get('commodity', '')))).upper()
            b_code_raw = row.get('bmc_code', row.get('bmcCode', row.get('BMCCode', row.get('hub_code', row.get('fromNode', row.get('from_node_id', ''))))))
            b_code = norm_code(b_code_raw)
            if '_' in b_code:
                b_code = b_code.split('_')[-1]
            
            key3 = (s_code, p_code, m_type)
            if key3 not in milk_summary_agg:
                milk_summary_agg[key3] = {'quantity': 0.0, 'noOftrips': 0}
            milk_summary_agg[key3]['quantity'] += float(row.get('quantity', row.get('Quantity', 0.0)))
            milk_summary_agg[key3]['noOftrips'] += int(row.get('noOftrips', row.get('noOfTrips', row.get('no_of_trips', 0))))

            key2 = (p_code, m_type)
            if key2 not in plant_milk_summary_agg:
                plant_milk_summary_agg[key2] = {'quantity': 0.0, 'noOftrips': 0}
            plant_milk_summary_agg[key2]['quantity'] += float(row.get('quantity', row.get('Quantity', 0.0)))
            plant_milk_summary_agg[key2]['noOftrips'] += int(row.get('noOftrips', row.get('noOfTrips', row.get('no_of_trips', 0))))
            
            if b_code:
                key4 = (s_code, b_code, p_code, m_type)
                if key4 not in bmc_milk_summary_agg:
                    bmc_milk_summary_agg[key4] = {'quantity': 0.0, 'noOftrips': 0}
                bmc_milk_summary_agg[key4]['quantity'] += float(row.get('quantity', row.get('Quantity', 0.0)))
                bmc_milk_summary_agg[key4]['noOftrips'] += int(row.get('noOftrips', row.get('noOfTrips', row.get('no_of_trips', 0))))
        print(f"[milk_summary] Aggregated keys available: {list(milk_summary_agg.keys())}")
        
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
                    "suppliername": supp_name
                }
                for mt in dynamic_milk_types:
                    supp_data[mt] = 0.0
                supp_data["BMC"] = []
                
                for _, r in group.iterrows():
                    b_code_full = str(r.get('BMCCode', ''))
                    b_code = b_code_full.split('_')[-1] if '_' in b_code_full else b_code_full
                    prod = str(r.get('commodity', '')).strip().upper()
                    cap = float(safe_val(r.get('capacity', 0)))
                    
                    bmc_entry = {
                        "BMCCode": b_code,
                        "BMCName": api_dict.get(b_code, str(r.get('name', '')))
                    }
                    bmc_total = 0.0
                    for mt in dynamic_milk_types:
                        val = cap if prod == mt else 0.0
                        bmc_entry[mt] = val
                        supp_data[mt] = supp_data.get(mt, 0.0) + val
                        bmc_total += val
                    if prod and prod not in dynamic_milk_types:
                        bmc_entry[prod] = cap
                        supp_data[prod] = supp_data.get(prod, 0.0) + cap
                        bmc_total += cap
                    bmc_entry["TotalSupply"] = bmc_total
                    supp_data['BMC'].append(bmc_entry)
                    
                supp_data['Total Supply'] = sum(
                    supp_data.get(k, 0.0) for k in supp_data 
                    if k not in ['suppliercode', 'suppliername', 'BMC', 'Total Supply']
                )
                format_2.append(supp_data)
        result_doc['supplierProductSupply'] = format_2
        
        # 3. suppliercode, suppliername, all vehicle name key
        format_3 = []
        if not df_input_veh.empty:
            grouped_veh = df_input_veh.groupby('SupplierCluster')
            for supp_code, group in grouped_veh:
                supp_name = api_dict.get(str(supp_code), "")
                
                supp_constraints = constraints_map.get(str(supp_code).strip(), {})
                is_lenient = supp_constraints.get("isLenient")
                bmc_min = supp_constraints.get("bmcMinQuantitySupply", [])
                plant_fixed = supp_constraints.get("plantFixedDemand", [])
                
                veh_data = {
                    "suppliercode": supp_code, 
                    "suppliername": supp_name,
                    "isLenient": is_lenient,
                    "bmcMinQuantitySupply": bmc_min,
                    "plantFixedDemand": plant_fixed
                }
                for col in group.columns:
                    if col.startswith('V') and len(col) == 3:
                        veh_data[col] = int(group[col].sum())
                format_3.append(veh_data)
        result_doc['supplierVehicles'] = format_3
        
        # Dynamically create substitution mapping from MilkSubstitution sheet
        sub_map = {}
        if not df_milk_sub.empty:
            from_col = next((c for c in df_milk_sub.columns if 'from' in str(c).lower()), 'FromMilk')
            to_col = next((c for c in df_milk_sub.columns if 'to' in str(c).lower()), 'ToMilk')
            if from_col in df_milk_sub.columns and to_col in df_milk_sub.columns:
                for _, s_row in df_milk_sub.iterrows():
                    fm = str(s_row[from_col]).strip().upper()
                    tm = str(s_row[to_col]).strip().upper()
                    if fm and tm and fm != 'NAN' and tm != 'NAN':
                        sub_map[f"{fm} TO {tm}"] = tm
        
        def map_product(prod):
            prod_upper = str(prod).upper().strip()
            if prod_upper in sub_map:
                return sub_map[prod_upper]
            if ' TO ' in prod_upper:
                return prod_upper.split(' TO ')[-1].strip()
            return prod

        # Format 4 from 'Total Supply (Max Util)'
        format_4 = []
        if not df_total_supply.empty:
            df_total_supply['From Node ID'] = df_total_supply['From Node ID'].astype(str)
            df_total_supply['To Node ID'] = df_total_supply['To Node ID'].astype(str)
            df_total_supply['SupplierCode'] = df_total_supply['From Node ID'].map(bmc_supp_code_map)
            df_total_supply['SupplierName'] = df_total_supply['From Node ID'].map(bmc_supp_map)
            prod_col = 'Base Milk' if 'Base Milk' in df_total_supply.columns else 'Product / Milk Type'
            if prod_col in df_total_supply.columns:
                df_total_supply['Product / Milk Type'] = df_total_supply[prod_col].apply(map_product)
            else:
                df_total_supply['Product / Milk Type'] = ''
                
            g4 = df_total_supply.groupby(['SupplierCode', 'To Node ID', 'Product / Milk Type'])
            for (supp, plant, prod), group in g4:
                dist = float(group['Total Distance'].sum()) if 'Total Distance' in group else float(group['Distance (km)'].sum()) if 'Distance (km)' in group else 0.0
                
                # Retrieve before quantities from the API data using normalized keys
                key = (norm_code(supp), norm_code(plant), norm_code(prod).upper())
                api_q = milk_summary_agg.get(key, {'quantity': 0.0, 'noOftrips': 0})
                if key not in milk_summary_agg:
                    print(f"[milk_summary mismatch] No match for route key {key}. Available keys: {list(milk_summary_agg.keys())}")
                before_quantity = api_q['quantity']
                before_nooftrip = api_q['noOftrips']
                before_distance = dist * before_nooftrip
                
                format_4.append({
                    "Supplier": supp, "SupplierName": api_dict.get(str(supp), ""),
                    "Plant": plant, "PlantName": api_dict.get(str(plant), ""),
                    "ProductType": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "Distance": dist,
                    "Total Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0,
                    "beforeQuantity": before_quantity,
                    "beforeDistance": before_distance,
                    "beforeNoofTrip": before_nooftrip
                })

        # 5, 6, 7, 8 from 'Routes (Max Utilized)'
        format_5 = []
        format_6 = []
        format_7 = []
        format_8 = []
        if not df_routes.empty:
            df_routes['From Node ID'] = df_routes['From Node ID'].astype(str)
            df_routes['To Node ID'] = df_routes['To Node ID'].astype(str)
            df_routes['SupplierCode'] = df_routes['From Node ID'].map(bmc_supp_code_map)
            df_routes['SupplierName'] = df_routes['From Node ID'].map(bmc_supp_map)
            df_routes['Product / Milk Type'] = df_routes['Product / Milk Type'].apply(map_product)

                
            # Format 5: Supplier, BMCCode, PlantCode, ProductType, flow, distance, trips, before quantities
            g5 = df_routes.groupby(['SupplierCode', 'From Node ID', 'To Node ID', 'Product / Milk Type'])
            for (supp, bmc, plant, prod), group in g5:
                actual_bmc = str(bmc).split('_')[-1] if '_' in str(bmc) else str(bmc)
                dist = float(group['Distance (km)'].sum())
                
                # Retrieve before quantities (prefer BMC-specific key if available from API, otherwise fallback to Supplier-Plant summary)
                key4 = (norm_code(supp), norm_code(actual_bmc), norm_code(plant), norm_code(prod).upper())
                key3 = (norm_code(supp), norm_code(plant), norm_code(prod).upper())
                api_q = bmc_milk_summary_agg.get(key4, milk_summary_agg.get(key3, {'quantity': 0.0, 'noOftrips': 0}))
                
                before_quantity = api_q['quantity']
                before_nooftrip = api_q['noOftrips']
                before_distance = dist * before_nooftrip

                format_5.append({
                    "Supplier": supp, "SupplierName": api_dict.get(str(supp), ""),
                    "BMCCode": actual_bmc, "BMCName": api_dict.get(actual_bmc, ""),
                    "PlantCode": plant, "PlantName": api_dict.get(str(plant), ""),
                    "ProductType": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "TotalDistance": dist,
                    "Total Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0,
                    "beforeQuantity": before_quantity,
                    "beforeDistance": before_distance,
                    "beforeNoofTrip": before_nooftrip
                })
                
            # Format 6: Plant, BMCCode, all product name keys
            g6 = df_routes.groupby(['To Node ID', 'From Node ID'])
            for (plant, bmc), group in g6:
                actual_bmc = str(bmc).split('_')[-1] if '_' in str(bmc) else str(bmc)
                d6 = {
                    "Plant": plant, "PlantName": api_dict.get(str(plant), ""),
                    "BMCCode": actual_bmc, "BMCName": api_dict.get(actual_bmc, "")
                }
                for mt in dynamic_milk_types:
                    d6[mt] = 0.0
                for _, r in group.iterrows():
                    prod = str(r['Product / Milk Type']).strip().upper()
                    if prod and prod not in d6:
                        d6[prod] = 0.0
                    if prod in d6:
                        d6[prod] += float(r.get('Dispatch Quantity', 0.0))
                format_6.append(d6)
                
            # Format 7: Plant, ProductType, Flow Quantity, TotalDistance, Total No.of Trips, before quantities
            g7 = df_routes.groupby(['To Node ID', 'Product / Milk Type'])
            for (plant, prod), group in g7:
                dist = float(group['Distance (km)'].sum())
                key2 = (norm_code(plant), norm_code(prod).upper())
                api_q = plant_milk_summary_agg.get(key2, {'quantity': 0.0, 'noOftrips': 0})
                
                before_quantity = api_q['quantity']
                before_nooftrip = api_q['noOftrips']
                before_distance = dist * before_nooftrip

                format_7.append({
                    "Plant": plant, "PlantName": api_dict.get(str(plant), ""),
                    "ProductType": prod,
                    "Dispatch Quantity": float(group['Dispatch Quantity'].sum()) if 'Dispatch Quantity' in group else 0.0,
                    "TotalDistance": dist,
                    "Total No.of Trips": int(group['Total Vehicles'].sum()) if 'Total Vehicles' in group else 0,
                    "beforeQuantity": before_quantity,
                    "beforeDistance": before_distance,
                    "beforeNoofTrip": before_nooftrip
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

async def save_final_reports(request_id):
    try:
        output_path = os.path.join(optimizer_solver.OUTPUT_FOLDER, f"results_{request_id}.xlsx")
        final_report_path = os.path.join(optimizer_solver.OUTPUT_FOLDER, f"finalreports_{request_id}.xlsx")
        target_sheets_map = [
            ('Plant Wise Dispatch (Max Util)', 'Plant Wise Dispatch'),
            ('BMC Wise Dispatch (Max Util)', 'BMC Wise Dispatch')
        ]
        
        if not os.path.exists(output_path):
            print(f"Results file not found at {output_path} for finalreports generation.")
            return

        res_xls = pd.ExcelFile(output_path)
        res_sheet_names = res_xls.sheet_names
        
        with pd.ExcelWriter(final_report_path) as writer:
            wrote_any_final = False
            for src_name, dest_name in target_sheets_map:
                if src_name in res_sheet_names:
                    df_sheet = pd.read_excel(res_xls, src_name)
                    df_sheet.to_excel(writer, sheet_name=dest_name, index=False)
                    wrote_any_final = True
                    
            veh_s_name = next((s for s in res_sheet_names if str(s).strip().startswith('BMC Vehicle Allocation (Max')), None)
            if veh_s_name:
                df_veh_final = pd.read_excel(res_xls, veh_s_name)
                if not df_veh_final.empty:
                    # Ignore rows where Dispatch Quantity is zero
                    disp_col = next((c for c in df_veh_final.columns if str(c).strip().lower() == 'dispatch quantity'), None)
                    if disp_col:
                        df_veh_final = df_veh_final[pd.to_numeric(df_veh_final[disp_col], errors='coerce').fillna(0) != 0].copy()
                    
                    # Remove columns from 'SupplierCluster' to 'Left Quantity' inclusive
                    cols_list = list(df_veh_final.columns)
                    sc_col = next((c for c in cols_list if str(c).strip().lower() == 'suppliercluster'), None)
                    lq_col = next((c for c in cols_list if str(c).strip().lower() == 'left quantity'), None)
                    if sc_col and lq_col and cols_list.index(sc_col) <= cols_list.index(lq_col):
                        start_idx = cols_list.index(sc_col)
                        end_idx = cols_list.index(lq_col)
                        cols_to_drop = cols_list[start_idx:end_idx + 1]
                        df_veh_final = df_veh_final.drop(columns=cols_to_drop)
                        
                df_veh_final.to_excel(writer, sheet_name='BMC Vehicle Allocation', index=False)
                wrote_any_final = True
                
            if not wrote_any_final:
                pd.DataFrame([{"Message": "No data"}]).to_excel(writer, sheet_name='Empty', index=False)
                
        res_xls.close()
        print(f"Saved finalreports Excel at {final_report_path}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error generating finalreports for {request_id}: {e}")

async def poll_requests():
    # Environment.JOB_ID check removed so that the task can start and pause dynamically
        
    await DatabaseConnection.connect()
    
    opt_repo = OptimizationRequestsRepository()
    plants_repo = RequestPlantsRepository()
    mmc_repo = RequestMMCsRepository()
    vehicles_repo = RequestVehiclesRepository()
    settings_repo = RequestSettingsRepository()
    mapping_repo = RequestPlantSupplierMappingRepository()
    constraints_repo = RequestConstraintsRepository()
    product_config_repo = RequestProductConfigurationsRepository()
    
    print("Background worker started. Polling for pending requests...")
    is_paused = False
    
    while True:
        try:
            from dotenv import dotenv_values
            import os
            env_vars = dotenv_values(".env")
            default_job = os.environ.get("JOB", os.environ.get("job", "false"))
            job_val = env_vars.get("JOB", env_vars.get("job", default_job))
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
            req_constraints = await constraints_repo.collection.find({"requestId": request_id}).to_list(length=None)
            req_product_config = await product_config_repo.collection.find({"requestId": request_id}).to_list(length=None)
            
            master_data = fetch_master_data()
            master_dict = {str(d.get('code')): d for d in master_data}
            
            dist_dict = {}
            
            def norm_code(val):
                if pd.isna(val):
                    return ""
                s = str(val).strip()
                if s.endswith(".0"):
                    s = s[:-2]
                return s

            try:
                db = DatabaseConnection.client["Network-Planner"] if DatabaseConnection.client else DatabaseConnection.get_db()
                dist_coll = db["BMCPlantDistance"]
                dist_docs = await dist_coll.find({}).to_list(length=None)
                for doc in dist_docs:
                    b_c = norm_code(doc.get("BMC Code", ""))
                    p_c = norm_code(doc.get("Plant Code", ""))
                    try:
                        d_val = float(doc.get("Distance", 0.0))
                        if pd.isna(d_val):
                            d_val = 0.0
                    except (ValueError, TypeError):
                        d_val = 0.0
                    dist_dict[(b_c, p_c)] = d_val
                    if "_" in b_c:
                        raw_b_c = b_c.split("_", 1)[-1]
                        if (raw_b_c, p_c) not in dist_dict:
                            dist_dict[(raw_b_c, p_c)] = d_val
            except Exception as e:
                print(f"Error reading Distance from Network-Planner.BMCPlantDistance collection: {e}")
            
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
                            "PlantCode": p_code, "Plant": plant_name, "Supplier": supplier_code,
                            "BMCCode": bmc_node_id, "BMC": bmc_name, "commodity": m["productCode"]
                        })
            
            all_plant_codes = list(set(
                [str(rp["plantCode"]).strip() for rp in req_plants if "plantCode" in rp] +
                [str(m["plantCode"]).strip() for m in req_mappings if "plantCode" in m]
            ))
            unique_bmcs = {}
            for rm in req_mmcs:
                if "mmcCode" in rm:
                    b_code = str(rm["mmcCode"]).strip()
                    s_code = str(rm.get("supplierCode", "")).strip()
                    if (s_code, b_code) not in unique_bmcs:
                        unique_bmcs[(s_code, b_code)] = rm
                        
            for (s_code, b_code_str), _ in unique_bmcs.items():
                supp_name = master_dict.get(s_code, {}).get('name', s_code)
                bmc_node_id = f"{s_code}_{b_code_str}" if s_code else b_code_str
                
                for p_code_str in all_plant_codes:
                    bmc_id_norm = norm_code(bmc_node_id)
                    b_code_norm = norm_code(b_code_str)
                    p_code_norm = norm_code(p_code_str)
                    
                    dist_val = dist_dict.get((bmc_id_norm, p_code_norm), dist_dict.get((b_code_norm, p_code_norm), 0.0))
                    dist = math.ceil(dist_val)
                    
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
                zero_dist_rows = []
                for row in df_distance[df_distance['Distance'] == 0.0].to_dict('records'):
                    zero_dist_rows.append({str(k): (v.item() if hasattr(v, 'item') else (None if pd.isna(v) else v)) for k, v in row.items()})
                await opt_repo.collection.update_one(
                    {"requestId": request_id},
                    {"$set": {
                        "status": "Failed",
                        "completedOn": datetime.utcnow(),
                        "error": {"distanceMapping": zero_dist_rows}
                    }}
                )
                print(f"Request {request_id} failed: zero distance found in distance mapping.")
                continue
            
            lenient_map = {}
            for c in req_constraints:
                sc = str(c.get("supplierCode", "")).strip()
                is_lenient = c.get("isLenient")
                if is_lenient is True or str(is_lenient).strip().lower() in ("true", "yes", "1"):
                    lenient_map[sc] = "yes"
                else:
                    lenient_map[sc] = "no"
            
            v_alloc_data = []
            supplier_codes = list(set([m["supplierCode"] for m in req_mmcs]))
            for s_code in supplier_codes:
                supply_outside_val = lenient_map.get(str(s_code).strip(), "no")
                row = {
                    "SupplierCluster": s_code, "SupplierSubCluster": "SubCluster_01_A", "Strategy": "Least Vehicle Strategy",
                    "FlowLowMarginPercentage": 0, "FlowHighMarginPercentage": 0, "SupplyOutSide": supply_outside_val,
                    "V07": 0, "V10": 0, "V12": 0, "V15": 0, "V20": 0, "V25": 0, "V30": 0, "V35": 0
                }
                has_vehicles = False
                for v in req_vehicles:
                    if v["supplierCode"] == s_code:
                        has_vehicles = True
                        vt = v["vehicleType"].upper().replace(' ', '')
                        count = v.get("vehicleCount", 0)
                        # if count == 0:
                        #     count = 1000
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
            
            # 1. MilkWiseSplit from RequestConstraints (bmcMinQuantitySupply)
            milk_wise_split_rows = []
            for c in req_constraints:
                s_code = str(c.get("supplierCode", "")).strip()
                for bmc_item in c.get("bmcMinQuantitySupply", []):
                    milk_type = str(bmc_item.get("product", "")).strip()
                    min_qty = bmc_item.get("value", 0.0)
                    try:
                        min_qty_float = float(min_qty) if min_qty is not None else 0.0
                    except (ValueError, TypeError):
                        min_qty_float = 0.0
                    if s_code and milk_type:
                        milk_wise_split_rows.append({
                            "SupplierCluster": s_code, "MilkType": milk_type, "MinQuantity": min_qty_float
                        })
            df_milkwise_split = pd.DataFrame(milk_wise_split_rows) if milk_wise_split_rows else pd.DataFrame(columns=["SupplierCluster", "MilkType", "MinQuantity"])
            
            # 2. SupplierPlantConsumption from RequestConstraints (plantFixedDemand)
            import re
            def to_pascal_case(s):
                if not s:
                    return ""
                return "".join(word.capitalize() for word in re.split(r'[\s_-]+', str(s).strip()) if word)

            supplier_plant_consumption_rows = []
            for c in req_constraints:
                s_code = str(c.get("supplierCode", "")).strip()
                for item in c.get("plantFixedDemand", []):
                    plant_code = str(item.get("plantCode", "")).strip()
                    milk_type = str(item.get("product", "")).strip()
                    raw_type = str(item.get("type", "")).strip()
                    val = item.get("value", 0.0)
                    try:
                        val_float = float(val) if val is not None else 0.0
                    except (ValueError, TypeError):
                        val_float = 0.0
                    if s_code and plant_code:
                        supplier_plant_consumption_rows.append({
                            "Supplier": s_code, "Plant": plant_code, "MilkType": milk_type,
                            "Type": to_pascal_case(raw_type), "Value": val_float
                        })
            df_supplier_plant_consumption = pd.DataFrame(supplier_plant_consumption_rows) if supplier_plant_consumption_rows else pd.DataFrame(columns=["Supplier", "Plant", "MilkType", "Type", "Value"])
            
            # 3. MilkSubstitution from RequestProductConfigurations
            sub_candidates_start = []
            sub_candidates_next = []
            for pc in req_product_config:
                can_convert = str(pc.get("canBeConvert", "")).strip()
                if can_convert and can_convert != "-" and can_convert.lower() != "null":
                    prod = str(pc.get("product", "")).strip()
                    derived = str(pc.get("derivedFrom", "")).strip()
                    item_dict = {"from": prod, "to": can_convert, "is_start": (derived in ("-", "", "null"))}
                    if item_dict["is_start"]:
                        sub_candidates_start.append(item_dict)
                    else:
                        sub_candidates_next.append(item_dict)

            milk_substitution_rows = []
            for start_item in sub_candidates_start:
                milk_substitution_rows.append({
                    "FromMilk": start_item["from"], "ToMilk": start_item["to"],
                    "ConversionFactor": 1, "Priority": 1, "Penalty": 10
                })
                curr_to = start_item["to"]
                while True:
                    match = next((item for item in sub_candidates_next if item["from"] == curr_to), None)
                    if not match:
                        break
                    sub_candidates_next.remove(match)
                    milk_substitution_rows.append({
                        "FromMilk": match["from"], "ToMilk": match["to"],
                        "ConversionFactor": 1, "Priority": 2, "Penalty": 10
                    })
                    curr_to = match["to"]

            for leftover in sub_candidates_next:
                milk_substitution_rows.append({
                    "FromMilk": leftover["from"], "ToMilk": leftover["to"],
                    "ConversionFactor": 1, "Priority": 2, "Penalty": 10
                })
            df_milk_substitution = pd.DataFrame(milk_substitution_rows) if milk_substitution_rows else pd.DataFrame(columns=["FromMilk", "ToMilk", "ConversionFactor", "Priority", "Penalty"])
            
            # 4. MilkConfig from RequestProductConfigurations & substitution chains
            bonus_factors_map = {}
            default_bonuses = [0.6, 0.4, 0.2, 0.1, 0.05]
            
            sub_map_chains = {}
            all_to_nodes = set()
            for r in milk_substitution_rows:
                fm = r["FromMilk"]
                tm = r["ToMilk"]
                if fm not in sub_map_chains:
                    sub_map_chains[fm] = []
                sub_map_chains[fm].append(tm)
                all_to_nodes.add(tm)

            chain_roots = [r["FromMilk"] for r in milk_substitution_rows if r["FromMilk"] not in all_to_nodes]
            all_from_nodes = [r["FromMilk"] for r in milk_substitution_rows]
            search_starts = chain_roots + all_from_nodes

            visited_nodes = set()
            for start_node in search_starts:
                if start_node in visited_nodes:
                    continue
                curr = start_node
                step = 0
                while curr and curr not in visited_nodes:
                    visited_nodes.add(curr)
                    if curr not in bonus_factors_map:
                        b_val = default_bonuses[step] if step < len(default_bonuses) else 0.0
                        bonus_factors_map[curr] = b_val
                    next_list = sub_map_chains.get(curr, [])
                    curr = next_list[0] if next_list else None
                    step += 1

            milk_config_rows = []
            for pc in req_product_config:
                prod_val = str(pc.get("product", "")).strip()
                if prod_val:
                    t_bonus = bonus_factors_map.get(prod_val, 0.0)
                    milk_config_rows.append({
                        "MilkType": prod_val, "Priority": "", "Group": prod_val,
                        "Aliases": prod_val, "TransportBonusFactor": t_bonus, "IsRawMilk": "Yes"
                    })
            df_milk_config = pd.DataFrame(milk_config_rows).drop_duplicates(subset=["MilkType"]) if milk_config_rows else pd.DataFrame(columns=["MilkType", "Priority", "Group", "Aliases", "TransportBonusFactor", "IsRawMilk"])
            
            output_dir = "uploads"
            os.makedirs(output_dir, exist_ok=True)
            excel_path = os.path.join(output_dir, f"request_{request_id}.xlsx")
            
            with pd.ExcelWriter(excel_path) as writer:
                df_nodes.to_excel(writer, sheet_name="Nodes", index=False)
                df_distance.to_excel(writer, sheet_name="Distance", index=False)
                df_mapping.to_excel(writer, sheet_name="Plant_BMC_Mapping", index=False)
                df_vehicle_alloc.to_excel(writer, sheet_name="Vehicle Supplier Allocation", index=False)
                df_vehicle_type.to_excel(writer, sheet_name="Vehicle Type", index=False)
                df_milkwise_split.to_excel(writer, sheet_name="MilkWiseSplit", index=False)
                df_supplier_plant_consumption.to_excel(writer, sheet_name="SupplierPlantConsumption", index=False)
                df_milk_substitution.to_excel(writer, sheet_name="MilkSubstitution", index=False)
                df_milk_config.to_excel(writer, sheet_name="MilkConfig", index=False)
                
            parsed_nodes = optimizer_solver.parse_excel_nodes(excel_path)
            # Use process_job_in_background which writes the result data
            optimizer_solver.process_job_in_background(job_id=request_id, network_id=network_id, nodes=parsed_nodes, transport_cost_per_km=0.02, excel_file_path=excel_path)
            
            await process_excel_and_save(request_id, excel_path, master_dict)
            await save_final_reports(request_id)
            
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
