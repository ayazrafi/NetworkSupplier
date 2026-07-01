import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.workzone import WorkZoneRepository
from src.repositories.organization import OrganizationRepository

class WorkZoneService:
    def __init__(self):
        self.repository = WorkZoneRepository()
        self.org_repository = OrganizationRepository()

    async def create(self, wz_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate Organization exists
        org = await self.org_repository.get_by_id("OrganizationId", wz_data["OrganizationId"])
        if not org:
            raise ValueError(f"Organization with ID '{wz_data['OrganizationId']}' does not exist.")

        # Validate unique code
        existing = await self.repository.get_by_code(wz_data["WorkZoneCode"])
        if existing:
            raise ValueError(f"WorkZone with code '{wz_data['WorkZoneCode']}' already exists.")

        from bson import ObjectId
        now = datetime.utcnow()
        wz_data["WorkZoneId"] = str(ObjectId())
        wz_data["CreatedBy"] = created_by
        wz_data["CreatedDate"] = now
        wz_data["UpdatedBy"] = created_by
        wz_data["UpdatedDate"] = now

        return await self.repository.create(wz_data)

    async def update(self, wz_id: str, wz_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("WorkZoneId", wz_id)
        if not existing:
            raise KeyError(f"WorkZone with ID '{wz_id}' not found.")

        # Validate Organization if it is being changed
        if "OrganizationId" in wz_data:
            org = await self.org_repository.get_by_id("OrganizationId", wz_data["OrganizationId"])
            if not org:
                raise ValueError(f"Organization with ID '{wz_data['OrganizationId']}' does not exist.")

        wz_data["UpdatedBy"] = updated_by
        wz_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("WorkZoneId", wz_id, wz_data)
        if not updated_doc:
            raise RuntimeError("Failed to update WorkZone record.")
        return updated_doc

    async def delete(self, wz_id: str) -> bool:
        existing = await self.repository.get_by_id("WorkZoneId", wz_id)
        if not existing:
            raise KeyError(f"WorkZone with ID '{wz_id}' not found.")
        return await self.repository.delete("WorkZoneId", wz_id)

    async def get_by_id(self, wz_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("WorkZoneId", wz_id)
        if not existing:
            raise KeyError(f"WorkZone with ID '{wz_id}' not found.")
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
