import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.mapping import (
    ClusterSubClusterMappingRepository,
    VehicleClusterMappingRepository,
    VehicleSubClusterMappingRepository
)
from src.repositories.cluster import ClusterRepository
from src.repositories.subcluster import SubClusterRepository
from src.repositories.vehicle import VehicleRepository

class ClusterSubClusterMappingService:
    def __init__(self):
        self.repository = ClusterSubClusterMappingRepository()
        self.cluster_repository = ClusterRepository()
        self.subcluster_repository = SubClusterRepository()

    async def create(self, mapping_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        cid = mapping_data["ClusterId"]
        scid = mapping_data["SubClusterId"]

        # Validate Cluster exists
        if not await self.cluster_repository.get_by_id("ClusterId", cid):
            raise ValueError(f"Cluster with ID '{cid}' does not exist.")

        # Validate SubCluster exists
        if not await self.subcluster_repository.get_by_id("SubClusterId", scid):
            raise ValueError(f"SubCluster with ID '{scid}' does not exist.")

        # Prevent duplicate mappings
        if await self.repository.check_duplicate(cid, scid):
            raise ValueError(f"Mapping between Cluster '{cid}' and SubCluster '{scid}' already exists.")

        now = datetime.utcnow()
        mapping_data["MappingId"] = str(uuid.uuid4())
        mapping_data["CreatedBy"] = created_by
        mapping_data["CreatedDate"] = now
        mapping_data["UpdatedBy"] = created_by
        mapping_data["UpdatedDate"] = now

        return await self.repository.create(mapping_data)

    async def update(self, mapping_id: str, mapping_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")

        cid = mapping_data.get("ClusterId", existing["ClusterId"])
        scid = mapping_data.get("SubClusterId", existing["SubClusterId"])

        if "ClusterId" in mapping_data and not await self.cluster_repository.get_by_id("ClusterId", cid):
            raise ValueError(f"Cluster with ID '{cid}' does not exist.")

        if "SubClusterId" in mapping_data and not await self.subcluster_repository.get_by_id("SubClusterId", scid):
            raise ValueError(f"SubCluster with ID '{scid}' does not exist.")

        if (cid != existing["ClusterId"] or scid != existing["SubClusterId"]) and await self.repository.check_duplicate(cid, scid):
            raise ValueError(f"Mapping between Cluster '{cid}' and SubCluster '{scid}' already exists.")

        mapping_data["UpdatedBy"] = updated_by
        mapping_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("MappingId", mapping_id, mapping_data)
        if not updated_doc:
            raise RuntimeError("Failed to update mapping record.")
        return updated_doc

    async def delete(self, mapping_id: str) -> bool:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")
        return await self.repository.delete("MappingId", mapping_id)

    async def get_by_id(self, mapping_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")
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


class VehicleClusterMappingService:
    def __init__(self):
        self.repository = VehicleClusterMappingRepository()
        self.vehicle_repository = VehicleRepository()
        self.cluster_repository = ClusterRepository()

    async def create(self, mapping_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        vid = mapping_data["VehicleId"]
        cid = mapping_data["ClusterId"]

        # Validate Vehicle exists
        if not await self.vehicle_repository.get_by_id("VehicleId", vid):
            raise ValueError(f"Vehicle with ID '{vid}' does not exist.")

        # Validate Cluster exists
        if not await self.cluster_repository.get_by_id("ClusterId", cid):
            raise ValueError(f"Cluster with ID '{cid}' does not exist.")

        # Prevent duplicate mappings
        if await self.repository.check_duplicate(vid, cid):
            raise ValueError(f"Mapping between Vehicle '{vid}' and Cluster '{cid}' already exists.")

        now = datetime.utcnow()
        mapping_data["MappingId"] = str(uuid.uuid4())
        mapping_data["CreatedBy"] = created_by
        mapping_data["CreatedDate"] = now
        mapping_data["UpdatedBy"] = created_by
        mapping_data["UpdatedDate"] = now

        return await self.repository.create(mapping_data)

    async def update(self, mapping_id: str, mapping_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")

        vid = mapping_data.get("VehicleId", existing["VehicleId"])
        cid = mapping_data.get("ClusterId", existing["ClusterId"])

        if "VehicleId" in mapping_data and not await self.vehicle_repository.get_by_id("VehicleId", vid):
            raise ValueError(f"Vehicle with ID '{vid}' does not exist.")

        if "ClusterId" in mapping_data and not await self.cluster_repository.get_by_id("ClusterId", cid):
            raise ValueError(f"Cluster with ID '{cid}' does not exist.")

        if (vid != existing["VehicleId"] or cid != existing["ClusterId"]) and await self.repository.check_duplicate(vid, cid):
            raise ValueError(f"Mapping between Vehicle '{vid}' and Cluster '{cid}' already exists.")

        mapping_data["UpdatedBy"] = updated_by
        mapping_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("MappingId", mapping_id, mapping_data)
        if not updated_doc:
            raise RuntimeError("Failed to update mapping record.")
        return updated_doc

    async def delete(self, mapping_id: str) -> bool:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")
        return await self.repository.delete("MappingId", mapping_id)

    async def get_by_id(self, mapping_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")
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


class VehicleSubClusterMappingService:
    def __init__(self):
        self.repository = VehicleSubClusterMappingRepository()
        self.vehicle_repository = VehicleRepository()
        self.subcluster_repository = SubClusterRepository()

    async def create(self, mapping_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        vid = mapping_data["VehicleId"]
        scid = mapping_data["SubClusterId"]

        # Validate Vehicle exists
        if not await self.vehicle_repository.get_by_id("VehicleId", vid):
            raise ValueError(f"Vehicle with ID '{vid}' does not exist.")

        # Validate SubCluster exists
        if not await self.subcluster_repository.get_by_id("SubClusterId", scid):
            raise ValueError(f"SubCluster with ID '{scid}' does not exist.")

        # Prevent duplicate mappings
        if await self.repository.check_duplicate(vid, scid):
            raise ValueError(f"Mapping between Vehicle '{vid}' and SubCluster '{scid}' already exists.")

        now = datetime.utcnow()
        mapping_data["MappingId"] = str(uuid.uuid4())
        mapping_data["CreatedBy"] = created_by
        mapping_data["CreatedDate"] = now
        mapping_data["UpdatedBy"] = created_by
        mapping_data["UpdatedDate"] = now

        return await self.repository.create(mapping_data)

    async def update(self, mapping_id: str, mapping_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")

        vid = mapping_data.get("VehicleId", existing["VehicleId"])
        scid = mapping_data.get("SubClusterId", existing["SubClusterId"])

        if "VehicleId" in mapping_data and not await self.vehicle_repository.get_by_id("VehicleId", vid):
            raise ValueError(f"Vehicle with ID '{vid}' does not exist.")

        if "SubClusterId" in mapping_data and not await self.subcluster_repository.get_by_id("SubClusterId", scid):
            raise ValueError(f"SubCluster with ID '{scid}' does not exist.")

        if (vid != existing["VehicleId"] or scid != existing["SubClusterId"]) and await self.repository.check_duplicate(vid, scid):
            raise ValueError(f"Mapping between Vehicle '{vid}' and SubCluster '{scid}' already exists.")

        mapping_data["UpdatedBy"] = updated_by
        mapping_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("MappingId", mapping_id, mapping_data)
        if not updated_doc:
            raise RuntimeError("Failed to update mapping record.")
        return updated_doc

    async def delete(self, mapping_id: str) -> bool:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")
        return await self.repository.delete("MappingId", mapping_id)

    async def get_by_id(self, mapping_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("MappingId", mapping_id)
        if not existing:
            raise KeyError(f"Mapping with ID '{mapping_id}' not found.")
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
