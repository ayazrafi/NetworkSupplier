from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.cluster import ClusterCreate, ClusterUpdate, ClusterResponse
from src.services.cluster import ClusterService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/cluster", tags=["Cluster Master"])
cluster_service = ClusterService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_cluster(cluster_in: ClusterCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_cluster = await cluster_service.create(cluster_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Cluster created successfully",
            "data": {
                "cluster": ClusterResponse(**new_cluster)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{cluster_id}", response_model=Dict[str, Any])
async def update_cluster(cluster_id: str, cluster_in: ClusterUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_cluster = await cluster_service.update(cluster_id, cluster_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Cluster updated successfully",
            "data": {
                "cluster": ClusterResponse(**updated_cluster)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{cluster_id}", response_model=Dict[str, Any])
async def delete_cluster(cluster_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await cluster_service.delete(cluster_id)
        return {
            "success": True,
            "message": "Cluster deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{cluster_id}", response_model=Dict[str, Any])
async def get_cluster_by_id(cluster_id: str, current_user: dict = Depends(get_current_user)):
    try:
        cluster = await cluster_service.get_by_id(cluster_id)
        return {
            "success": True,
            "message": "Cluster retrieved successfully",
            "data": {
                "cluster": ClusterResponse(**cluster)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_cluster_list(
    isActive: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    sortBy: str = Query("CreatedDate"),
    sortOrder: str = Query("desc", description="asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if isActive is not None:
        query["IsActive"] = isActive
        
    s_order = -1 if sortOrder.lower() == "desc" else 1
    docs, total = await cluster_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [ClusterResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "Cluster list retrieved successfully",
        "data": {
            "clusters": serialized,
            "count": total
        }
    }
