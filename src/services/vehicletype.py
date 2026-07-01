import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.vehicletype import VehicleTypeRepository
from src.repositories.workzone import WorkZoneRepository

class VehicleTypeService:
    def __init__(self):
        self.repository = VehicleTypeRepository()
        self.wz_repository = WorkZoneRepository()

    async def create(self, vt_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate WorkZone exists
        wz = await self.wz_repository.get_by_id("WorkZoneId", vt_data["WorkZoneId"])
        if not wz:
            raise ValueError(f"WorkZone with ID '{vt_data['WorkZoneId']}' does not exist.")

        # Validate unique code
        existing = await self.repository.get_by_code(vt_data["VehicleTypeCode"])
        if existing:
            raise ValueError(f"VehicleType with code '{vt_data['VehicleTypeCode']}' already exists.")

        now = datetime.utcnow()
        vt_data["VehicleTypeId"] = str(uuid.uuid4())
        vt_data["CreatedBy"] = created_by
        vt_data["CreatedDate"] = now
        vt_data["UpdatedBy"] = created_by
        vt_data["UpdatedDate"] = now

        return await self.repository.create(vt_data)

    async def update(self, vt_id: str, vt_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("VehicleTypeId", vt_id)
        if not existing:
            raise KeyError(f"VehicleType with ID '{vt_id}' not found.")

        # Validate WorkZone if it is being changed
        if "WorkZoneId" in vt_data:
            wz = await self.wz_repository.get_by_id("WorkZoneId", vt_data["WorkZoneId"])
            if not wz:
                raise ValueError(f"WorkZone with ID '{vt_data['WorkZoneId']}' does not exist.")

        vt_data["UpdatedBy"] = updated_by
        vt_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("VehicleTypeId", vt_id, vt_data)
        if not updated_doc:
            raise RuntimeError("Failed to update VehicleType record.")
        return updated_doc

    async def delete(self, vt_id: str) -> bool:
        existing = await self.repository.get_by_id("VehicleTypeId", vt_id)
        if not existing:
            raise KeyError(f"VehicleType with ID '{vt_id}' not found.")
        return await self.repository.delete("VehicleTypeId", vt_id)

    async def get_by_id(self, vt_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("VehicleTypeId", vt_id)
        if not existing:
            raise KeyError(f"VehicleType with ID '{vt_id}' not found.")
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
