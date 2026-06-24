from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository

class PlantRepository(BaseRepository):
    def __init__(self):
        super().__init__("PlantMaster")

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"PlantCode": code})
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        return None
