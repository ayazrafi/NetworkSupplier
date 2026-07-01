from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.product import ProductCreate, ProductUpdate, ProductResponse
from src.services.product import ProductService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/product", tags=["Product Master"])
product_service = ProductService()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_product(product_in: ProductCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_product = await product_service.create(product_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Product created successfully",
            "data": {
                "product": ProductResponse(**new_product)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{product_id}", response_model=Dict[str, Any])
async def update_product(product_id: str, product_in: ProductUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_product = await product_service.update(product_id, product_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Product updated successfully",
            "data": {
                "product": ProductResponse(**updated_product)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{product_id}", response_model=Dict[str, Any])
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await product_service.delete(product_id)
        return {
            "success": True,
            "message": "Product deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{product_id}", response_model=Dict[str, Any])
async def get_product_by_id(product_id: str, current_user: dict = Depends(get_current_user)):
    try:
        product = await product_service.get_by_id(product_id)
        return {
            "success": True,
            "message": "Product retrieved successfully",
            "data": {
                "product": ProductResponse(**product)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=Dict[str, Any])
async def get_product_list(
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
    docs, total = await product_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [ProductResponse(**item) for item in docs]

    return {
        "success": True,
        "message": "Product list retrieved successfully",
        "data": {
            "products": serialized,
            "count": total
        }
    }
