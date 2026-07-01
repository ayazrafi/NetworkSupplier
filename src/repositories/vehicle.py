from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, serialize_doc

class VehicleRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleMaster")

    async def get_by_type(self, vehicle_type: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"VehicleType": vehicle_type})
        return serialize_doc(doc)
