from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.bmc import BMCRepository
from src.repositories.workzone import WorkZoneRepository

class BMCService:
    def __init__(self):
        self.repository = BMCRepository()
        self.wz_repository = WorkZoneRepository()

    async def create(self, bmc_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate WorkZone exists
        wz = await self.wz_repository.get_by_id("WorkZoneId", bmc_data["WorkZoneId"])
        if not wz:
            raise ValueError(f"WorkZone with ID '{bmc_data['WorkZoneId']}' does not exist.")

        # Enforce unique BMC code
        existing = await self.repository.get_by_code(bmc_data["BMCCode"])
        if existing:
            raise ValueError(f"BMC with code '{bmc_data['BMCCode']}' already exists.")

        now = datetime.utcnow()
        bmc_data["BMCId"] = str(ObjectId())
        bmc_data["CreatedBy"] = created_by
        bmc_data["CreatedDate"] = now
        bmc_data["UpdatedBy"] = created_by
        bmc_data["UpdatedDate"] = now

        return await self.repository.create(bmc_data)

    async def update(self, bmc_id: str, bmc_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("BMCId", bmc_id)
        if not existing:
            raise KeyError(f"BMC with ID '{bmc_id}' not found.")

        # Validate WorkZone if changing
        if "WorkZoneId" in bmc_data:
            wz = await self.wz_repository.get_by_id("WorkZoneId", bmc_data["WorkZoneId"])
            if not wz:
                raise ValueError(f"WorkZone with ID '{bmc_data['WorkZoneId']}' does not exist.")

        bmc_data["UpdatedBy"] = updated_by
        bmc_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("BMCId", bmc_id, bmc_data)
        if not updated_doc:
            raise RuntimeError("Failed to update BMC record.")
        return updated_doc

    async def delete(self, bmc_id: str) -> bool:
        existing = await self.repository.get_by_id("BMCId", bmc_id)
        if not existing:
            raise KeyError(f"BMC with ID '{bmc_id}' not found.")
        return await self.repository.delete("BMCId", bmc_id)

    async def get_by_id(self, bmc_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("BMCId", bmc_id)
        if not existing:
            raise KeyError(f"BMC with ID '{bmc_id}' not found.")
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
