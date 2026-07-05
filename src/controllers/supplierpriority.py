from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.supplierpriority import SupplierPriorityCreate, SupplierPriorityUpdate, SupplierPriorityResponse
from src.services.supplierpriority import SupplierPriorityService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/supplier-priority", tags=["Supplier Priority"])
service = SupplierPriorityService()

@router.post("/sync", response_model=Dict[str, Any])
async def sync_supplier_priority(current_user: dict = Depends(get_current_user)):
    try:
        result = await service.sync_from_external_api(current_user["userId"])
        return {
            "success": True,
            "message": "Supplier priority data synced successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_supplier_priority(item_in: SupplierPriorityCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_item = await service.create(item_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Created successfully",
            "data": {
                "supplier_priority": SupplierPriorityResponse(**new_item)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{item_id}", response_model=Dict[str, Any])
async def update_supplier_priority(item_id: str, item_in: SupplierPriorityUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_item = await service.update(item_id, item_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Updated successfully",
            "data": {
                "supplier_priority": SupplierPriorityResponse(**updated_item)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{item_id}", response_model=Dict[str, Any])
async def delete_supplier_priority(item_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await service.delete(item_id)
        return {
            "success": True,
            "message": "Deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{item_id}", response_model=Dict[str, Any])
async def get_supplier_priority_by_id(item_id: str, current_user: dict = Depends(get_current_user)):
    try:
        item = await service.get_by_id(item_id)
        return {
            "success": True,
            "message": "Retrieved successfully",
            "data": {
                "supplier_priority": SupplierPriorityResponse(**item)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_supplier_priority_list(
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
    docs, total = await service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [SupplierPriorityResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "List retrieved successfully",
        "data": {
            "supplier_priorities": serialized,
            "count": total
        }
    }
