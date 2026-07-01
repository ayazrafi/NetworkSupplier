import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.organization import OrganizationRepository

class OrganizationService:
    def __init__(self):
        self.repository = OrganizationRepository()

    async def create(self, org_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_code(org_data["OrganizationCode"])
        if existing:
            raise ValueError(f"Organization with code '{org_data['OrganizationCode']}' already exists.")

        from bson import ObjectId
        now = datetime.utcnow()
        org_data["OrganizationId"] = str(ObjectId())
        org_data["CreatedBy"] = created_by
        org_data["CreatedDate"] = now
        org_data["UpdatedBy"] = created_by
        org_data["UpdatedDate"] = now

        return await self.repository.create(org_data)

    async def update(self, org_id: str, org_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("OrganizationId", org_id)
        if not existing:
            raise KeyError(f"Organization with ID '{org_id}' not found.")

        org_data["UpdatedBy"] = updated_by
        org_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("OrganizationId", org_id, org_data)
        if not updated_doc:
            raise RuntimeError("Failed to update Organization record.")
        return updated_doc

    async def delete(self, org_id: str) -> bool:
        existing = await self.repository.get_by_id("OrganizationId", org_id)
        if not existing:
            raise KeyError(f"Organization with ID '{org_id}' not found.")
        return await self.repository.delete("OrganizationId", org_id)

    async def get_by_id(self, org_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("OrganizationId", org_id)
        if not existing:
            raise KeyError(f"Organization with ID '{org_id}' not found.")
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
