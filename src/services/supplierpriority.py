from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Tuple, List
import httpx
from src.repositories.supplierpriority import SupplierPriorityRepository

class SupplierPriorityService:
    def __init__(self):
        self.repository = SupplierPriorityRepository()

    async def create(self, data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        data["SupplierPriorityId"] = str(ObjectId())
        data["CreatedBy"] = created_by
        data["CreatedDate"] = now
        data["UpdatedBy"] = created_by
        data["UpdatedDate"] = now
        return await self.repository.create(data)

    async def update(self, id: str, data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("SupplierPriorityId", id)
        if not existing:
            raise KeyError(f"SupplierPriority with ID '{id}' not found.")

        data["UpdatedBy"] = updated_by
        data["UpdatedDate"] = datetime.utcnow()
        
        updated_doc = await self.repository.update("SupplierPriorityId", id, data)
        if not updated_doc:
            raise RuntimeError("Failed to update record.")
        return updated_doc

    async def delete(self, id: str) -> bool:
        existing = await self.repository.get_by_id("SupplierPriorityId", id)
        if not existing:
            raise KeyError(f"SupplierPriority with ID '{id}' not found.")
        return await self.repository.delete("SupplierPriorityId", id)

    async def get_by_id(self, id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("SupplierPriorityId", id)
        if not existing:
            raise KeyError(f"SupplierPriority with ID '{id}' not found.")
        return existing

    async def get_list(
        self, query: Dict[str, Any], skip: int = 0, limit: int = 10,
        sort_by: str = "CreatedDate", sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repository.get_list(query, skip, limit, sort_by, sort_order)

    async def sync_from_external_api(self, created_by: str = "system") -> Dict[str, Any]:
        url = "https://apinode1.secutrak.in/mobileApiDairyM/getSupplierPriority"
        headers = {
            "Authorization": "Bearer 40Y8h3xcr3nGBOQ154d154PH23mSj770"
        }
        files = {
            "AccessToken": (None, "40Y8h3xcr3nGBOQ154d154PH23mSj770")
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, headers=headers, files=files)
            
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch data from API. Status: {response.status_code}")
            
        json_data = response.json()
        if json_data.get("Status") != "success":
            raise RuntimeError(f"API returned error: {json_data.get('message', 'Unknown error')}")
            
        items = json_data.get("Data", [])
        
        now = datetime.utcnow()
        documents = []
        for item in items:
            documents.append({
                "SupplierPriorityId": str(ObjectId()),
                "PlantCode": str(item.get("plant_code", "")),
                "SupplierCode": str(item.get("supplier_code", "")),
                "ProductCode": str(item.get("product_code", "")),
                "WorkZoneId": ObjectId("6a4a3f1af35f5b895f72b130"),
                "IsActive": True,
                "CreatedBy": created_by,
                "CreatedDate": now,
                "UpdatedBy": created_by,
                "UpdatedDate": now
            })
            
        # Clear and insert newly fetched data
        count = await self.repository.clear_and_insert_many(documents)
        return {"synced_count": count}
