from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from src.services.organization import OrganizationService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/organization", tags=["Organization Master"])
organization_service = OrganizationService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_organization(org_in: OrganizationCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_org = await organization_service.create(org_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Organization created successfully",
            "data": {
                "organization": OrganizationResponse(**new_org)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{org_id}", response_model=Dict[str, Any])
async def update_organization(org_id: str, org_in: OrganizationUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_org = await organization_service.update(org_id, org_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Organization updated successfully",
            "data": {
                "organization": OrganizationResponse(**updated_org)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{org_id}", response_model=Dict[str, Any])
async def delete_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await organization_service.delete(org_id)
        return {
            "success": True,
            "message": "Organization deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{org_id}", response_model=Dict[str, Any])
async def get_organization_by_id(org_id: str, current_user: dict = Depends(get_current_user)):
    try:
        org = await organization_service.get_by_id(org_id)
        return {
            "success": True,
            "message": "Organization retrieved successfully",
            "data": {
                "organization": OrganizationResponse(**org)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_organization_list(
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
    docs, total = await organization_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [OrganizationResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "Organization list retrieved successfully",
        "data": {
            "organizations": serialized,
            "count": total
        }
    }
