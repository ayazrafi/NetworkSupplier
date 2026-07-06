from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.bmcsuppliermapping import BMCSupplierMappingRepository

class BMCSupplierMappingService:
    def __init__(self):
        self.repository = BMCSupplierMappingRepository()

    async def create(self, data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        data["BMCSupplierMappingId"] = str(ObjectId())
        data["CreatedBy"] = created_by
        data["CreatedDate"] = now
        data["UpdatedBy"] = created_by
        data["UpdatedDate"] = now
        return await self.repository.create(data)

    async def update(self, id: str, data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("BMCSupplierMappingId", id)
        if not existing:
            raise KeyError(f"BMCSupplierMapping with ID '{id}' not found.")

        data["UpdatedBy"] = updated_by
        data["UpdatedDate"] = datetime.utcnow()
        
        updated_doc = await self.repository.update("BMCSupplierMappingId", id, data)
        if not updated_doc:
            raise RuntimeError("Failed to update record.")
        return updated_doc

    async def delete(self, id: str) -> bool:
        existing = await self.repository.get_by_id("BMCSupplierMappingId", id)
        if not existing:
            raise KeyError(f"BMCSupplierMapping with ID '{id}' not found.")
        return await self.repository.delete("BMCSupplierMappingId", id)

    async def get_by_id(self, id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("BMCSupplierMappingId", id)
        if not existing:
            raise KeyError(f"BMCSupplierMapping with ID '{id}' not found.")
        return existing

    async def get_list(
        self, query: Dict[str, Any], skip: int = 0, limit: int = 10,
        sort_by: str = "CreatedDate", sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repository.get_list(query, skip, limit, sort_by, sort_order)
