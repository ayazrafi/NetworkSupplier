from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, convert_query_ids

class SupplierClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("SupplierClusterMapping")

    async def check_duplicate(self, supplier_id: str, cluster_id: str) -> bool:
        query = {
            "SupplierId": supplier_id, 
            "ClusterId": cluster_id
        }
        doc = await self.collection.find_one(convert_query_ids(query))
        return doc is not None


class VehicleSupplierMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleSupplierMapping")

    async def check_duplicate(self, vehicle_id: str, supplier_id: str) -> bool:
        query = {
            "VehicleId": vehicle_id, 
            "SupplierId": supplier_id
        }
        doc = await self.collection.find_one(convert_query_ids(query))
        return doc is not None


class VehicleClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleClusterMapping")

    async def check_duplicate(self, vehicle_id: str, cluster_id: str) -> bool:
        query = {
            "VehicleId": vehicle_id, 
            "ClusterId": cluster_id
        }
        doc = await self.collection.find_one(convert_query_ids(query))
        return doc is not None


class BMCSupplierClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("BMCSupplierClusterMapping")

    async def check_duplicate(self, bmc_id: str, supplier_id: str, cluster_id: str) -> bool:
        query = {
            "BMCId": bmc_id,
            "SupplierId": supplier_id, 
            "ClusterId": cluster_id
        }
        doc = await self.collection.find_one(convert_query_ids(query))
        return doc is not None
