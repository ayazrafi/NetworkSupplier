import asyncio
import os
import time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.config.db import DatabaseConnection
from src.repositories.request import (
    OptimizationRequestsRepository,
    RequestPlantsRepository,
    RequestMMCsRepository,
    RequestVehiclesRepository,
    RequestSettingsRepository
)
from src.repositories.plant import PlantRepository
from src.repositories.bmc import BMCRepository
from src.repositories.result import OptimizationResultsRepository

import optimizer_solver

async def poll_requests():
    await DatabaseConnection.connect()
    
    opt_repo = OptimizationRequestsRepository()
    plants_repo = RequestPlantsRepository()
    mmc_repo = RequestMMCsRepository()
    vehicles_repo = RequestVehiclesRepository()
    settings_repo = RequestSettingsRepository()
    
    db_plant_repo = PlantRepository()
    db_bmc_repo = BMCRepository()
    results_repo = OptimizationResultsRepository()

    print("Background worker started. Polling for pending requests...")
    
    while True:
        try:
            pending_req = await opt_repo.collection.find_one_and_update(
                {"status": "Pending"},
                {"$set": {"status": "InProgress", "startedOn": datetime.utcnow()}}
            )
            
            if not pending_req:
                await asyncio.sleep(10)
                continue
                
            request_id = pending_req["requestId"]
            job_id = str(pending_req["_id"])
            print(f"Processing Request: {request_id} (JobId: {request_id})")
            
            req_plants = await plants_repo.collection.find({"requestId": request_id}).to_list(length=None)
            req_mmcs = await mmc_repo.collection.find({"requestId": request_id}).to_list(length=None)
            req_vehicles = await vehicles_repo.collection.find({"requestId": request_id}).to_list(length=None)
            
            nodes = []
            
            for rp in req_plants:
                p_code = rp["plantCode"]
                db_plant = await db_plant_repo.collection.find_one({"PlantCode": p_code})
                lat = db_plant["Latitude"] if db_plant else 0.0
                lng = db_plant["Longitude"] if db_plant else 0.0
                
                nodes.append({
                    "node_id": p_code,
                    "type": "plant",
                    "lat": lat,
                    "lng": lng,
                    "commodity": rp["productCode"],
                    "demand": rp["demand"]
                })
                
            for rm in req_mmcs:
                m_code = rm["mmcCode"]
                db_bmc = await db_bmc_repo.collection.find_one({"BMCCode": m_code})
                lat = db_bmc["Latitude"] if db_bmc else 0.0
                lng = db_bmc["Longitude"] if db_bmc else 0.0
                
                nodes.append({
                    "node_id": m_code,
                    "type": "hub",
                    "lat": lat,
                    "lng": lng,
                    "commodity": rm["productCode"],
                    "capacity": rm["availableSupply"]
                })
                
            df_nodes = pd.DataFrame(nodes)
            
            df_mapping = pd.DataFrame([
                {"PlantCode": rp["plantCode"], "BMCCode": rm["mmcCode"], "commodity": rp["productCode"], "Supplier": rm["supplierCode"]}
                for rp in req_plants for rm in req_mmcs if rp["productCode"] == rm["productCode"]
            ])
            
            df_vehicle_type = pd.DataFrame([{"VehicleCode": v["vehicleType"], "To": 10} for v in req_vehicles]) 
            
            v_alloc_data = []
            for rm in req_mmcs:
                row = {"SupplierCluster": rm["supplierCode"]}
                for v in req_vehicles:
                    if v["supplierCode"] == rm["supplierCode"]:
                        row[v["vehicleType"].lower().replace(' ', '')] = v["vehicleCount"]
                v_alloc_data.append(row)
            df_vehicle_alloc = pd.DataFrame(v_alloc_data)

            output_dir = "uploads"
            os.makedirs(output_dir, exist_ok=True)
            excel_path = os.path.join(output_dir, f"request_{request_id}.xlsx")
            
            with pd.ExcelWriter(excel_path) as writer:
                df_nodes.to_excel(writer, sheet_name="Nodes", index=False)
                df_mapping.to_excel(writer, sheet_name="Plant_BMC_Mapping", index=False)
                df_vehicle_type.to_excel(writer, sheet_name="Vehicle Type", index=False)
                df_vehicle_alloc.to_excel(writer, sheet_name="VehicleSupplierAllocation", index=False)
                
            parsed_nodes = optimizer_solver.parse_excel_nodes(excel_path)
            farmers = [n for n in parsed_nodes if n['type'] == 'farmer']
            hubs = [n for n in parsed_nodes if n['type'] == 'hub']
            plants = [n for n in parsed_nodes if n['type'] == 'plant']
            geographies = [n for n in parsed_nodes if n['type'] == 'geography']
            
            res = optimizer_solver.solve_network_lp(farmers, hubs, plants, geographies, transport_cost_per_km=0.02, excel_file_path=excel_path)
            
            if res.get('status') in ('OPTIMAL', 'FEASIBLE'):
                routes = res.get('routes', [])
                for route in routes:
                    if route['from_type'] == 'hub' and route['to_type'] == 'plant':
                        # Find SupplierCode for this hub from mapping
                        supplier_code = ""
                        for rm in req_mmcs:
                            if rm["mmcCode"] == route['from_id']:
                                supplier_code = rm["supplierCode"]
                                break
                        
                        await results_repo.collection.insert_one({
                            "JobId": request_id,
                            "SupplierCode": supplier_code,
                            "PlantCode": route['to_id'],
                            "TotalDistance": route['distance'],
                            "TotalVehicleCount": route.get('total_vehicles', 0),
                            "MilkTypeCode": route['product_type'],
                            "TotalSupply": route['flow'],
                            "TotalDemand": route['flow']
                        })
                        
                await opt_repo.collection.update_one(
                    {"requestId": request_id},
                    {"$set": {"status": "Completed", "completedOn": datetime.utcnow()}}
                )
                print(f"Request {request_id} processed successfully.")
            else:
                await opt_repo.collection.update_one(
                    {"requestId": request_id},
                    {"$set": {"status": "Failed", "completedOn": datetime.utcnow()}}
                )
                print(f"Request {request_id} failed to solve.")
                
        except Exception as e:
            print(f"Error processing loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(poll_requests())
