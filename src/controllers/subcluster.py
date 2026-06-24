from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.subcluster import SubClusterCreate, SubClusterUpdate, SubClusterResponse
from src.services.subcluster import SubClusterService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/subcluster", tags=["SubCluster Master"])
subcluster_service = SubClusterService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_subcluster(subcluster_in: SubClusterCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_subcluster = await subcluster_service.create(subcluster_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "SubCluster created successfully",
            "data": {
                "subcluster": SubClusterResponse(**new_subcluster)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{subcluster_id}", response_model=Dict[str, Any])
async def update_subcluster(subcluster_id: str, subcluster_in: SubClusterUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_subcluster = await subcluster_service.update(subcluster_id, subcluster_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "SubCluster updated successfully",
            "data": {
                "subcluster": SubClusterResponse(**updated_subcluster)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{subcluster_id}", response_model=Dict[str, Any])
async def delete_subcluster(subcluster_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await subcluster_service.delete(subcluster_id)
        return {
            "success": True,
            "message": "SubCluster deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{subcluster_id}", response_model=Dict[str, Any])
async def get_subcluster_by_id(subcluster_id: str, current_user: dict = Depends(get_current_user)):
    try:
        subcluster = await subcluster_service.get_by_id(subcluster_id)
        return {
            "success": True,
            "message": "SubCluster retrieved successfully",
            "data": {
                "subcluster": SubClusterResponse(**subcluster)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_subcluster_list(
    clusterId: Optional[str] = Query(None, description="Filter by parent cluster ID"),
    isActive: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    sortBy: str = Query("CreatedDate"),
    sortOrder: str = Query("desc", description="asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if clusterId is not None:
        query["ClusterId"] = clusterId
    if isActive is not None:
        query["IsActive"] = isActive
        
    s_order = -1 if sortOrder.lower() == "desc" else 1
    docs, total = await subcluster_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [SubClusterResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "SubCluster list retrieved successfully",
        "data": {
            "subclusters": serialized,
            "count": total
        }
    }
