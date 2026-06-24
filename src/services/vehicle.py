import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.vehicle import VehicleRepository

class VehicleService:
    def __init__(self):
        self.repository = VehicleRepository()

    async def create(self, vehicle_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_type(vehicle_data["VehicleType"])
        if existing:
            raise ValueError(f"Vehicle type '{vehicle_data['VehicleType']}' already exists.")

        now = datetime.utcnow()
        vehicle_data["VehicleId"] = str(uuid.uuid4())
        vehicle_data["CreatedBy"] = created_by
        vehicle_data["CreatedDate"] = now
        vehicle_data["UpdatedBy"] = created_by
        vehicle_data["UpdatedDate"] = now

        return await self.repository.create(vehicle_data)

    async def update(self, vehicle_id: str, vehicle_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("VehicleId", vehicle_id)
        if not existing:
            raise KeyError(f"Vehicle with ID '{vehicle_id}' not found.")

        # Check unique constraint if renaming vehicle type
        if "VehicleType" in vehicle_data and vehicle_data["VehicleType"] != existing["VehicleType"]:
            dup = await self.repository.get_by_type(vehicle_data["VehicleType"])
            if dup:
                raise ValueError(f"Vehicle type '{vehicle_data['VehicleType']}' already exists.")

        vehicle_data["UpdatedBy"] = updated_by
        vehicle_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("VehicleId", vehicle_id, vehicle_data)
        if not updated_doc:
            raise RuntimeError("Failed to update Vehicle record.")
        return updated_doc

    async def delete(self, vehicle_id: str) -> bool:
        existing = await self.repository.get_by_id("VehicleId", vehicle_id)
        if not existing:
            raise KeyError(f"Vehicle with ID '{vehicle_id}' not found.")
        return await self.repository.delete("VehicleId", vehicle_id)

    async def get_by_id(self, vehicle_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("VehicleId", vehicle_id)
        if not existing:
            raise KeyError(f"Vehicle with ID '{vehicle_id}' not found.")
        return existing

    async def get_list(
        self, 
        query: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 10, 
        sort_by: str = "CreatedDate", 
        sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repository.get_list(query, skip, limit, sort_by, sort_order)
        
    async def get_all(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.repository.get_all(query)
