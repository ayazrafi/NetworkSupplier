from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.vehicletype import VehicleTypeCreate, VehicleTypeUpdate, VehicleTypeResponse
from src.services.vehicletype import VehicleTypeService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/vehicletype", tags=["VehicleType Master"])
vehicletype_service = VehicleTypeService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_vehicletype(vt_in: VehicleTypeCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_vt = await vehicletype_service.create(vt_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "VehicleType created successfully",
            "data": {
                "vehicletype": VehicleTypeResponse(**new_vt)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{vt_id}", response_model=Dict[str, Any])
async def update_vehicletype(vt_id: str, vt_in: VehicleTypeUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_vt = await vehicletype_service.update(vt_id, vt_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "VehicleType updated successfully",
            "data": {
                "vehicletype": VehicleTypeResponse(**updated_vt)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{vt_id}", response_model=Dict[str, Any])
async def delete_vehicletype(vt_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await vehicletype_service.delete(vt_id)
        return {
            "success": True,
            "message": "VehicleType deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{vt_id}", response_model=Dict[str, Any])
async def get_vehicletype_by_id(vt_id: str, current_user: dict = Depends(get_current_user)):
    try:
        vt = await vehicletype_service.get_by_id(vt_id)
        return {
            "success": True,
            "message": "VehicleType retrieved successfully",
            "data": {
                "vehicletype": VehicleTypeResponse(**vt)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_vehicletype_list(
    workZoneId: Optional[str] = Query(None, description="Filter by work zone ID"),
    isActive: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    sortBy: str = Query("CreatedDate"),
    sortOrder: str = Query("desc", description="asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if workZoneId is not None:
        query["WorkZoneId"] = workZoneId
    if isActive is not None:
        query["IsActive"] = isActive
        
    s_order = -1 if sortOrder.lower() == "desc" else 1
    docs, total = await vehicletype_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [VehicleTypeResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "VehicleType list retrieved successfully",
        "data": {
            "vehicletypes": serialized,
            "count": total
        }
    }
