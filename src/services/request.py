from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bson import ObjectId
from pymongo import ReturnDocument
from src.config.db import DatabaseConnection
from src.models.request import RequestCreateInput, UserProductConfigInput
from src.repositories.request import (
    OptimizationRequestsRepository,
    RequestPlantsRepository,
    RequestMMCsRepository,
    RequestVehiclesRepository,
    RequestSettingsRepository,
    RequestPlantSupplierMappingRepository,
    RequestConstraintsRepository,
    RequestProductConfigurationsRepository,
    UserProductConfigRepository
)

class RequestService:
    def __init__(self):
        self.opt_repository = OptimizationRequestsRepository()
        self.plants_repository = RequestPlantsRepository()
        self.mmc_repository = RequestMMCsRepository()
        self.vehicles_repository = RequestVehiclesRepository()
        self.settings_repository = RequestSettingsRepository()
        self.mapping_repository = RequestPlantSupplierMappingRepository()
        self.constraints_repository = RequestConstraintsRepository()
        self.product_config_repository = RequestProductConfigurationsRepository()
        self.user_product_config_repository = UserProductConfigRepository()


    async def _generate_request_id(self) -> str:
        db = DatabaseConnection.get_db()
        counter = await db["Counters"].find_one_and_update(
            {"_id": "requestId"},
            {"$inc": {"sequence_value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return f"REQ{counter['sequence_value']:04d}"

    async def create_request(self, request_in: RequestCreateInput, created_by: str) -> Dict[str, Any]:
        request_id = await self._generate_request_id()
        now = datetime.utcnow()

        # 1. Save Basic Information (OptimizationRequests)
        opt_req_doc = {
            "requestId": request_id,
            "requestName": request_in.requestName,
            "status": "Pending",
            "createdBy": created_by,
            "createdOn": now,
            "startedOn": None,
            "completedOn": None
        }
        created_opt_req = await self.opt_repository.create(opt_req_doc)

        opt_req_id = ObjectId(created_opt_req["_id"])

        # 2. Save Request Plants
        plant_docs = [
            {
                "requestId": request_id,
                "OptimizationRequestId": opt_req_id,
                "plantCode": p.plantCode,
                "productCode": p.product,
                "demand": p.demand
            }
            for p in request_in.plants
        ]
        if plant_docs:
            await self.plants_repository.collection.insert_many(plant_docs)

        # 3. Save Request MMCs
        mmc_docs = [
            {
                "requestId": request_id,
                "OptimizationRequestId": opt_req_id,
                "mmcCode": m.mmcCode,
                "supplierCode": m.supplierCode,
                "productCode": m.product,
                "availableSupply": m.supply
            }
            for m in request_in.mmcs
        ]
        if mmc_docs:
            await self.mmc_repository.collection.insert_many(mmc_docs)

        # 4. Save Request Vehicles
        vehicle_docs = [
            {
                "requestId": request_id,
                "OptimizationRequestId": opt_req_id,
                "supplierCode": v.supplierCode,
                "vehicleType": v.vehicleType,
                "vehicleCount": v.count
            }
            for v in request_in.vehicles
        ]
        if vehicle_docs:
            await self.vehicles_repository.collection.insert_many(vehicle_docs)

        # 5. Save Request Settings
        settings_doc = {
            "requestId": request_id,
            "OptimizationRequestId": opt_req_id,
            "maxDistance": request_in.maxDistance,
            "leaveQuantity": request_in.leaveQuantity,
            "tripType": request_in.tripType,
            "createdOn": now
        }
        await self.settings_repository.create(settings_doc)

        # 6. Save Request Plant Supplier Mappings
        mapping_docs = [
            {
                "requestId": request_id,
                "OptimizationRequestId": opt_req_id,
                "plantCode": p.plantCode,
                "supplierCode": p.supplierCode,
                "productCode": p.productCode
            }
            for p in request_in.plantSupplierMapping
        ]
        if mapping_docs:
            await self.mapping_repository.collection.insert_many(mapping_docs)

        # 7. Save Request Constraints
        if request_in.constraints:
            constraint_docs = [
                {
                    "requestId": request_id,
                    "OptimizationRequestId": opt_req_id,
                    **c.model_dump()
                }
                for c in request_in.constraints
            ]
            if constraint_docs:
                await self.constraints_repository.collection.insert_many(constraint_docs)

        # 8. Save Request Product Configurations
        if request_in.productConfiguration:
            product_config_docs = [
                {
                    "requestId": request_id,
                    "OptimizationRequestId": opt_req_id,
                    **p.model_dump()
                }
                for p in request_in.productConfiguration
            ]
            if product_config_docs:
                await self.product_config_repository.collection.insert_many(product_config_docs)

        return created_opt_req

    async def get_requests_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        query = {
            "createdOn": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        results = await self.opt_repository.get_all(query, sort_by="createdOn", sort_order=-1)
        for req in results:
            if "createdOn" in req and req["createdOn"] is not None:
                if isinstance(req["createdOn"], datetime):
                    req["createdOn"] = req["createdOn"] + timedelta(hours=5, minutes=30)
                elif isinstance(req["createdOn"], str):
                    try:
                        dt = datetime.fromisoformat(req["createdOn"].replace("Z", "+00:00"))
                        req["createdOn"] = (dt + timedelta(hours=5, minutes=30)).isoformat()
                    except (ValueError, TypeError):
                        pass
        return results

    async def update_request_status(self, job_id: str, new_status: str) -> Dict[str, Any]:
        query = {"$or": [{"requestId": job_id}, {"jobId": job_id}]}
        existing = await self.opt_repository.collection.find_one(query)
        if not existing:
            raise KeyError(f"Request not found for jobId: {job_id}")
            
        update_doc = {"$set": {"status": new_status}}
        if "error" in existing:
            update_doc["$set"]["error"] = {} if isinstance(existing.get("error"), dict) else ""
            
        updated = await self.opt_repository.collection.find_one_and_update(
            query,
            update_doc,
            return_document=ReturnDocument.AFTER
        )
        if updated:
            for k, v in list(updated.items()):
                if isinstance(v, ObjectId):
                    updated[k] = str(v)
            if "createdOn" in updated and isinstance(updated["createdOn"], datetime):
                updated["createdOn"] = updated["createdOn"] + timedelta(hours=5, minutes=30)
        return updated

    async def save_user_product_config(self, config_in: UserProductConfigInput) -> Dict[str, Any]:
        doc = {
            "groupId": config_in.groupId,
            "userId": config_in.userId,
            "data": [d.model_dump() for d in config_in.data],
            "updatedOn": datetime.utcnow()
        }
        query = {"groupId": config_in.groupId, "userId": config_in.userId}
        await self.user_product_config_repository.collection.delete_many(query)
        created = await self.user_product_config_repository.create(doc)
        if "updatedOn" in created and isinstance(created["updatedOn"], datetime):
            created["updatedOn"] = created["updatedOn"].isoformat()
        return created

    async def get_user_product_config(self, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        query = {"groupId": group_id, "userId": user_id}
        result = await self.user_product_config_repository.collection.find_one(query)
        if result and "_id" in result:
            result["_id"] = str(result["_id"])
        if result and "updatedOn" in result and isinstance(result["updatedOn"], datetime):
            result["updatedOn"] = result["updatedOn"].isoformat()
        return result

