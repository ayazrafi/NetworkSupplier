from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.bmc import BMCCreate, BMCUpdate, BMCResponse
from src.services.bmc import BMCService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/bmc", tags=["BMC Master"])
bmc_service = BMCService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_bmc(bmc_in: BMCCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_bmc = await bmc_service.create(bmc_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "BMC created successfully",
            "data": {
                "bmc": BMCResponse(**new_bmc)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{bmc_id}", response_model=Dict[str, Any])
async def update_bmc(bmc_id: str, bmc_in: BMCUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_bmc = await bmc_service.update(bmc_id, bmc_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "BMC updated successfully",
            "data": {
                "bmc": BMCResponse(**updated_bmc)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{bmc_id}", response_model=Dict[str, Any])
async def delete_bmc(bmc_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await bmc_service.delete(bmc_id)
        return {
            "success": True,
            "message": "BMC deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/search", response_model=Dict[str, Any])
async def search_bmc(
    q: str = Query(..., min_length=1, description="Search query matching code or name"),
    current_user: dict = Depends(get_current_user)
):
    query = {
        "$or": [
            {"BMCCode": {"$regex": q, "$options": "i"}},
            {"BMCName": {"$regex": q, "$options": "i"}}
        ]
    }
    results = await bmc_service.get_all(query)
    serialized = [BMCResponse(**item) for item in results]
    return {
        "success": True,
        "message": "Search completed successfully",
        "data": {
            "results": serialized,
            "count": len(serialized)
        }
    }

@router.get("/{bmc_id}", response_model=Dict[str, Any])
async def get_bmc_by_id(bmc_id: str, current_user: dict = Depends(get_current_user)):
    try:
        bmc = await bmc_service.get_by_id(bmc_id)
        return {
            "success": True,
            "message": "BMC retrieved successfully",
            "data": {
                "bmc": BMCResponse(**bmc)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_bmc_list(
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
    docs, total = await bmc_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [BMCResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "BMC list retrieved successfully",
        "data": {
            "bmcs": serialized,
            "count": total
        }
    }
