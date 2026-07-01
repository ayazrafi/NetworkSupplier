from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, serialize_doc

class BMCRepository(BaseRepository):
    def __init__(self):
        super().__init__("BMCMaster")

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"BMCCode": code})
        return serialize_doc(doc)
