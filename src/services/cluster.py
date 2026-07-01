import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.cluster import ClusterRepository
from src.repositories.workzone import WorkZoneRepository

class ClusterService:
    def __init__(self):
        self.repository = ClusterRepository()
        self.wz_repository = WorkZoneRepository()

    async def create(self, cluster_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate WorkZone exists
        wz = await self.wz_repository.get_by_id("WorkZoneId", cluster_data["WorkZoneId"])
        if not wz:
            raise ValueError(f"WorkZone with ID '{cluster_data['WorkZoneId']}' does not exist.")

        # Validate unique code
        existing = await self.repository.get_by_code(cluster_data["ClusterCode"])
        if existing:
            raise ValueError(f"Cluster with code '{cluster_data['ClusterCode']}' already exists.")

        now = datetime.utcnow()
        cluster_data["ClusterId"] = str(uuid.uuid4())
        cluster_data["CreatedBy"] = created_by
        cluster_data["CreatedDate"] = now
        cluster_data["UpdatedBy"] = created_by
        cluster_data["UpdatedDate"] = now

        return await self.repository.create(cluster_data)

    async def update(self, cluster_id: str, cluster_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("ClusterId", cluster_id)
        if not existing:
            raise KeyError(f"Cluster with ID '{cluster_id}' not found.")

        # Validate WorkZone if changing
        if "WorkZoneId" in cluster_data:
            wz = await self.wz_repository.get_by_id("WorkZoneId", cluster_data["WorkZoneId"])
            if not wz:
                raise ValueError(f"WorkZone with ID '{cluster_data['WorkZoneId']}' does not exist.")

        cluster_data["UpdatedBy"] = updated_by
        cluster_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("ClusterId", cluster_id, cluster_data)
        if not updated_doc:
            raise RuntimeError("Failed to update Cluster record.")
        return updated_doc

    async def delete(self, cluster_id: str) -> bool:
        existing = await self.repository.get_by_id("ClusterId", cluster_id)
        if not existing:
            raise KeyError(f"Cluster with ID '{cluster_id}' not found.")
        return await self.repository.delete("ClusterId", cluster_id)

    async def get_by_id(self, cluster_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("ClusterId", cluster_id)
        if not existing:
            raise KeyError(f"Cluster with ID '{cluster_id}' not found.")
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
