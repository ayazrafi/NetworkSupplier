from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, serialize_doc

class VehicleTypeRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleTypeMaster")

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"VehicleTypeCode": code})
        return serialize_doc(doc)
