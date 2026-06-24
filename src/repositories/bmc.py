from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository

class BMCRepository(BaseRepository):
    def __init__(self):
        super().__init__("BMCMaster")

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"BMCCode": code})
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        return None
