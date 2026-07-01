from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.plant import PlantCreate, PlantUpdate, PlantResponse
from src.services.plant import PlantService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/plant", tags=["Plant Master"])
plant_service = PlantService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_plant(plant_in: PlantCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_plant = await plant_service.create(plant_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Plant created successfully",
            "data": {
                "plant": PlantResponse(**new_plant)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{plant_id}", response_model=Dict[str, Any])
async def update_plant(plant_id: str, plant_in: PlantUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_plant = await plant_service.update(plant_id, plant_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Plant updated successfully",
            "data": {
                "plant": PlantResponse(**updated_plant)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{plant_id}", response_model=Dict[str, Any])
async def delete_plant(plant_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await plant_service.delete(plant_id)
        return {
            "success": True,
            "message": "Plant deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{plant_id}", response_model=Dict[str, Any])
async def get_plant_by_id(plant_id: str, current_user: dict = Depends(get_current_user)):
    try:
        plant = await plant_service.get_by_id(plant_id)
        return {
            "success": True,
            "message": "Plant retrieved successfully",
            "data": {
                "plant": PlantResponse(**plant)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_plant_list(
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
    docs, total = await plant_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [PlantResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "Plant list retrieved successfully",
        "data": {
            "plants": serialized,
            "count": total
        }
    }
