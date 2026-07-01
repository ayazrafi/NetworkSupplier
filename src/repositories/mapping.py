from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository

class SupplierClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("SupplierClusterMapping")

    async def check_duplicate(self, supplier_id: str, cluster_id: str) -> bool:
        doc = await self.collection.find_one({
            "SupplierId": supplier_id, 
            "ClusterId": cluster_id
        })
        return doc is not None


class VehicleSupplierMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleSupplierMapping")

    async def check_duplicate(self, vehicle_id: str, supplier_id: str) -> bool:
        doc = await self.collection.find_one({
            "VehicleId": vehicle_id, 
            "SupplierId": supplier_id
        })
        return doc is not None


class VehicleClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleClusterMapping")

    async def check_duplicate(self, vehicle_id: str, cluster_id: str) -> bool:
        doc = await self.collection.find_one({
            "VehicleId": vehicle_id, 
            "ClusterId": cluster_id
        })
        return doc is not None
