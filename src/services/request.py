from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId
from pymongo import ReturnDocument
from src.config.db import DatabaseConnection
from src.models.request import RequestCreateInput
from src.repositories.request import (
    OptimizationRequestsRepository,
    RequestPlantsRepository,
    RequestMMCsRepository,
    RequestVehiclesRepository,
    RequestSettingsRepository
)

class RequestService:
    def __init__(self):
        self.opt_repository = OptimizationRequestsRepository()
        self.plants_repository = RequestPlantsRepository()
        self.mmc_repository = RequestMMCsRepository()
        self.vehicles_repository = RequestVehiclesRepository()
        self.settings_repository = RequestSettingsRepository()

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
            "createdOn": now
        }
        await self.settings_repository.create(settings_doc)

        return created_opt_req

    async def get_requests_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        query = {
            "createdOn": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        return await self.opt_repository.get_all(query, sort_by="createdOn", sort_order=-1)
