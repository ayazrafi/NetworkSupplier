import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.plant import PlantRepository
from src.repositories.workzone import WorkZoneRepository

class PlantService:
    def __init__(self):
        self.repository = PlantRepository()
        self.wz_repository = WorkZoneRepository()

    async def create(self, plant_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate WorkZone exists
        wz = await self.wz_repository.get_by_id("WorkZoneId", plant_data["WorkZoneId"])
        if not wz:
            raise ValueError(f"WorkZone with ID '{plant_data['WorkZoneId']}' does not exist.")

        existing = await self.repository.get_by_code(plant_data["PlantCode"])
        if existing:
            raise ValueError(f"Plant with code '{plant_data['PlantCode']}' already exists.")

        now = datetime.utcnow()
        plant_data["PlantId"] = str(uuid.uuid4())
        plant_data["CreatedBy"] = created_by
        plant_data["CreatedDate"] = now
        plant_data["UpdatedBy"] = created_by
        plant_data["UpdatedDate"] = now

        return await self.repository.create(plant_data)

    async def update(self, plant_id: str, plant_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("PlantId", plant_id)
        if not existing:
            raise KeyError(f"Plant with ID '{plant_id}' not found.")

        # Validate WorkZone if changing
        if "WorkZoneId" in plant_data:
            wz = await self.wz_repository.get_by_id("WorkZoneId", plant_data["WorkZoneId"])
            if not wz:
                raise ValueError(f"WorkZone with ID '{plant_data['WorkZoneId']}' does not exist.")

        plant_data["UpdatedBy"] = updated_by
        plant_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("PlantId", plant_id, plant_data)
        if not updated_doc:
            raise RuntimeError("Failed to update Plant record.")
        return updated_doc

    async def delete(self, plant_id: str) -> bool:
        existing = await self.repository.get_by_id("PlantId", plant_id)
        if not existing:
            raise KeyError(f"Plant with ID '{plant_id}' not found.")
        return await self.repository.delete("PlantId", plant_id)

    async def get_by_id(self, plant_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("PlantId", plant_id)
        if not existing:
            raise KeyError(f"Plant with ID '{plant_id}' not found.")
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
