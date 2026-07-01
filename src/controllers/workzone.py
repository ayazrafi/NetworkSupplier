from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.workzone import WorkZoneCreate, WorkZoneUpdate, WorkZoneResponse
from src.services.workzone import WorkZoneService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/workzone", tags=["WorkZone Master"])
workzone_service = WorkZoneService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_workzone(wz_in: WorkZoneCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_wz = await workzone_service.create(wz_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "WorkZone created successfully",
            "data": {
                "workzone": WorkZoneResponse(**new_wz)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{wz_id}", response_model=Dict[str, Any])
async def update_workzone(wz_id: str, wz_in: WorkZoneUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_wz = await workzone_service.update(wz_id, wz_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "WorkZone updated successfully",
            "data": {
                "workzone": WorkZoneResponse(**updated_wz)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{wz_id}", response_model=Dict[str, Any])
async def delete_workzone(wz_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await workzone_service.delete(wz_id)
        return {
            "success": True,
            "message": "WorkZone deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{wz_id}", response_model=Dict[str, Any])
async def get_workzone_by_id(wz_id: str, current_user: dict = Depends(get_current_user)):
    try:
        wz = await workzone_service.get_by_id(wz_id)
        return {
            "success": True,
            "message": "WorkZone retrieved successfully",
            "data": {
                "workzone": WorkZoneResponse(**wz)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_workzone_list(
    organizationId: Optional[str] = Query(None, description="Filter by organization ID"),
    isActive: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    sortBy: str = Query("CreatedDate"),
    sortOrder: str = Query("desc", description="asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if organizationId is not None:
        query["OrganizationId"] = organizationId
    if isActive is not None:
        query["IsActive"] = isActive
        
    s_order = -1 if sortOrder.lower() == "desc" else 1
    docs, total = await workzone_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [WorkZoneResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "WorkZone list retrieved successfully",
        "data": {
            "workzones": serialized,
            "count": total
        }
    }
