from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from src.services.vehicle import VehicleService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/vehicle", tags=["Vehicle Master"])
vehicle_service = VehicleService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_vehicle(vehicle_in: VehicleCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_vehicle = await vehicle_service.create(vehicle_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Vehicle created successfully",
            "data": {
                "vehicle": VehicleResponse(**new_vehicle)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{vehicle_id}", response_model=Dict[str, Any])
async def update_vehicle(vehicle_id: str, vehicle_in: VehicleUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_vehicle = await vehicle_service.update(vehicle_id, vehicle_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Vehicle updated successfully",
            "data": {
                "vehicle": VehicleResponse(**updated_vehicle)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{vehicle_id}", response_model=Dict[str, Any])
async def delete_vehicle(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await vehicle_service.delete(vehicle_id)
        return {
            "success": True,
            "message": "Vehicle deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{vehicle_id}", response_model=Dict[str, Any])
async def get_vehicle_by_id(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    try:
        vehicle = await vehicle_service.get_by_id(vehicle_id)
        return {
            "success": True,
            "message": "Vehicle retrieved successfully",
            "data": {
                "vehicle": VehicleResponse(**vehicle)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_vehicle_list(
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
    docs, total = await vehicle_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [VehicleResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "Vehicle list retrieved successfully",
        "data": {
            "vehicles": serialized,
            "count": total
        }
    }
