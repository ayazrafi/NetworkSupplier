from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.supplier import SupplierCreate, SupplierUpdate, SupplierResponse
from src.services.supplier import SupplierService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/supplier", tags=["Supplier Master"])
supplier_service = SupplierService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_supplier(supplier_in: SupplierCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_supplier = await supplier_service.create(supplier_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Supplier created successfully",
            "data": {
                "supplier": SupplierResponse(**new_supplier)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{supplier_id}", response_model=Dict[str, Any])
async def update_supplier(supplier_id: str, supplier_in: SupplierUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_supplier = await supplier_service.update(supplier_id, supplier_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Supplier updated successfully",
            "data": {
                "supplier": SupplierResponse(**updated_supplier)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{supplier_id}", response_model=Dict[str, Any])
async def delete_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await supplier_service.delete(supplier_id)
        return {
            "success": True,
            "message": "Supplier deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{supplier_id}", response_model=Dict[str, Any])
async def get_supplier_by_id(supplier_id: str, current_user: dict = Depends(get_current_user)):
    try:
        supplier = await supplier_service.get_by_id(supplier_id)
        return {
            "success": True,
            "message": "Supplier retrieved successfully",
            "data": {
                "supplier": SupplierResponse(**supplier)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_supplier_list(
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
    docs, total = await supplier_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [SupplierResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "Supplier list retrieved successfully",
        "data": {
            "suppliers": serialized,
            "count": total
        }
    }
