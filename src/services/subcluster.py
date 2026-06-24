import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.subcluster import SubClusterRepository
from src.repositories.cluster import ClusterRepository

class SubClusterService:
    def __init__(self):
        self.repository = SubClusterRepository()
        self.cluster_repository = ClusterRepository()

    async def create(self, subcluster_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate parent cluster exists
        parent_cluster = await self.cluster_repository.get_by_id("ClusterId", subcluster_data["ClusterId"])
        if not parent_cluster:
            raise ValueError(f"Parent Cluster with ID '{subcluster_data['ClusterId']}' does not exist.")

        # Validate unique subcluster code
        existing = await self.repository.get_by_code(subcluster_data["SubClusterCode"])
        if existing:
            raise ValueError(f"SubCluster with code '{subcluster_data['SubClusterCode']}' already exists.")

        now = datetime.utcnow()
        subsub_id = str(uuid.uuid4())
        subcluster_data["SubClusterId"] = subsub_id
        subcluster_data["CreatedBy"] = created_by
        subcluster_data["CreatedDate"] = now
        subcluster_data["UpdatedBy"] = created_by
        subcluster_data["UpdatedDate"] = now

        return await self.repository.create(subcluster_data)

    async def update(self, subcluster_id: str, subcluster_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("SubClusterId", subcluster_id)
        if not existing:
            raise KeyError(f"SubCluster with ID '{subcluster_id}' not found.")

        # Validate parent cluster if it's changing
        if "ClusterId" in subcluster_data:
            parent_cluster = await self.cluster_repository.get_by_id("ClusterId", subcluster_data["ClusterId"])
            if not parent_cluster:
                raise ValueError(f"Parent Cluster with ID '{subcluster_data['ClusterId']}' does not exist.")

        subcluster_data["UpdatedBy"] = updated_by
        subcluster_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("SubClusterId", subcluster_id, subcluster_data)
        if not updated_doc:
            raise RuntimeError("Failed to update SubCluster record.")
        return updated_doc

    async def delete(self, subcluster_id: str) -> bool:
        existing = await self.repository.get_by_id("SubClusterId", subcluster_id)
        if not existing:
            raise KeyError(f"SubCluster with ID '{subcluster_id}' not found.")
        return await self.repository.delete("SubClusterId", subcluster_id)

    async def get_by_id(self, subcluster_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("SubClusterId", subcluster_id)
        if not existing:
            raise KeyError(f"SubCluster with ID '{subcluster_id}' not found.")
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
        
    async def get_all(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.repository.get_all(query)
