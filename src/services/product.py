from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.product import ProductRepository
from src.repositories.workzone import WorkZoneRepository


class ProductService:
    def __init__(self):
        self.repository = ProductRepository()
        self.wz_repository = WorkZoneRepository()

    async def create(self, product_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate WorkZone exists
        wz = await self.wz_repository.get_by_id("WorkZoneId", product_data["WorkZoneId"])
        if not wz:
            raise ValueError(f"WorkZone with ID '{product_data['WorkZoneId']}' does not exist.")

        # Validate unique code
        existing = await self.repository.get_by_code(product_data["ProductCode"])
        if existing:
            raise ValueError(f"Product with code '{product_data['ProductCode']}' already exists.")

        now = datetime.utcnow()
        product_data["ProductId"] = str(ObjectId())
        product_data["CreatedBy"] = created_by
        product_data["CreatedDate"] = now
        product_data["UpdatedBy"] = created_by
        product_data["UpdatedDate"] = now

        return await self.repository.create(product_data)

    async def update(self, product_id: str, product_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("ProductId", product_id)
        if not existing:
            raise KeyError(f"Product with ID '{product_id}' not found.")

        # Validate WorkZone if it is being changed
        if "WorkZoneId" in product_data:
            wz = await self.wz_repository.get_by_id("WorkZoneId", product_data["WorkZoneId"])
            if not wz:
                raise ValueError(f"WorkZone with ID '{product_data['WorkZoneId']}' does not exist.")

        product_data["UpdatedBy"] = updated_by
        product_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("ProductId", product_id, product_data)
        if not updated_doc:
            raise RuntimeError("Failed to update Product record.")
        return updated_doc

    async def delete(self, product_id: str) -> bool:
        existing = await self.repository.get_by_id("ProductId", product_id)
        if not existing:
            raise KeyError(f"Product with ID '{product_id}' not found.")
        return await self.repository.delete("ProductId", product_id)

    async def get_by_id(self, product_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("ProductId", product_id)
        if not existing:
            raise KeyError(f"Product with ID '{product_id}' not found.")
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
