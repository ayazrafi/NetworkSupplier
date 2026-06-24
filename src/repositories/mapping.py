from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository

class ClusterSubClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("ClusterSubClusterMapping")

    async def check_duplicate(self, cluster_id: str, subcluster_id: str) -> bool:
        doc = await self.collection.find_one({
            "ClusterId": cluster_id, 
            "SubClusterId": subcluster_id
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


class VehicleSubClusterMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("VehicleSubClusterMapping")

    async def check_duplicate(self, vehicle_id: str, subcluster_id: str) -> bool:
        doc = await self.collection.find_one({
            "VehicleId": vehicle_id, 
            "SubClusterId": subcluster_id
        })
        return doc is not None
