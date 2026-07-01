from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, serialize_doc

class WorkZoneRepository(BaseRepository):
    def __init__(self):
        super().__init__("WorkZoneMaster")

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"WorkZoneCode": code})
        return serialize_doc(doc)
