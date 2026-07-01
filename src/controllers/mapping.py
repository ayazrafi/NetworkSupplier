from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.mapping import (
    SupplierClusterMappingCreate, SupplierClusterMappingUpdate, SupplierClusterMappingResponse,
    VehicleSupplierMappingCreate, VehicleSupplierMappingUpdate, VehicleSupplierMappingResponse,
    VehicleClusterMappingCreate, VehicleClusterMappingUpdate, VehicleClusterMappingResponse
)
from src.services.mapping import (
    SupplierClusterMappingService,
    VehicleSupplierMappingService,
    VehicleClusterMappingService
)
from src.middlewares.auth import get_current_user

# 1. Supplier-Cluster Router
sc_router = APIRouter(prefix="/api/v1/supplier-cluster-mapping", tags=["Supplier-Cluster Mapping"])
sc_service = SupplierClusterMappingService()

@sc_router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_sc_mapping(mapping_in: SupplierClusterMappingCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_mapping = await sc_service.create(mapping_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping created successfully",
            "data": {
                "mapping": SupplierClusterMappingResponse(**new_mapping)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@sc_router.put("/{mapping_id}", response_model=Dict[str, Any])
async def update_sc_mapping(mapping_id: str, mapping_in: SupplierClusterMappingUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_mapping = await sc_service.update(mapping_id, mapping_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping updated successfully",
            "data": {
                "mapping": SupplierClusterMappingResponse(**updated_mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@sc_router.delete("/{mapping_id}", response_model=Dict[str, Any])
async def delete_sc_mapping(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await sc_service.delete(mapping_id)
        return {
            "success": True,
            "message": "Mapping deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@sc_router.get("/{mapping_id}", response_model=Dict[str, Any])
async def get_sc_mapping_by_id(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        mapping = await sc_service.get_by_id(mapping_id)
        return {
            "success": True,
            "message": "Mapping retrieved successfully",
            "data": {
                "mapping": SupplierClusterMappingResponse(**mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@sc_router.get("", response_model=Dict[str, Any])
async def get_sc_mapping_list(
    supplierId: Optional[str] = Query(None),
    clusterId: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if supplierId is not None:
        query["SupplierId"] = supplierId
    if clusterId is not None:
        query["ClusterId"] = clusterId
    if isActive is not None:
        query["IsActive"] = isActive
        
    docs, total = await sc_service.get_list(query, skip, limit)
    serialized = [SupplierClusterMappingResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Mappings retrieved successfully",
        "data": {
            "mappings": serialized,
            "count": total
        }
    }


# 2. Vehicle-Supplier Router
vs_router = APIRouter(prefix="/api/v1/vehicle-supplier-mapping", tags=["Vehicle-Supplier Mapping"])
vs_service = VehicleSupplierMappingService()

@vs_router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_vs_mapping(mapping_in: VehicleSupplierMappingCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_mapping = await vs_service.create(mapping_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping created successfully",
            "data": {
                "mapping": VehicleSupplierMappingResponse(**new_mapping)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@vs_router.put("/{mapping_id}", response_model=Dict[str, Any])
async def update_vs_mapping(mapping_id: str, mapping_in: VehicleSupplierMappingUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_mapping = await vs_service.update(mapping_id, mapping_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping updated successfully",
            "data": {
                "mapping": VehicleSupplierMappingResponse(**updated_mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@vs_router.delete("/{mapping_id}", response_model=Dict[str, Any])
async def delete_vs_mapping(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await vs_service.delete(mapping_id)
        return {
            "success": True,
            "message": "Mapping deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@vs_router.get("/{mapping_id}", response_model=Dict[str, Any])
async def get_vs_mapping_by_id(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        mapping = await vs_service.get_by_id(mapping_id)
        return {
            "success": True,
            "message": "Mapping retrieved successfully",
            "data": {
                "mapping": VehicleSupplierMappingResponse(**mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@vs_router.get("", response_model=Dict[str, Any])
async def get_vs_mapping_list(
    vehicleId: Optional[str] = Query(None),
    supplierId: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if vehicleId is not None:
        query["VehicleId"] = vehicleId
    if supplierId is not None:
        query["SupplierId"] = supplierId
    if isActive is not None:
        query["IsActive"] = isActive
        
    docs, total = await vs_service.get_list(query, skip, limit)
    serialized = [VehicleSupplierMappingResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Mappings retrieved successfully",
        "data": {
            "mappings": serialized,
            "count": total
        }
    }


# 3. Vehicle-Cluster Router
vc_router = APIRouter(prefix="/api/v1/vehicle-cluster-mapping", tags=["Vehicle-Cluster Mapping"])
vc_service = VehicleClusterMappingService()

@vc_router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_vc_mapping(mapping_in: VehicleClusterMappingCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_mapping = await vc_service.create(mapping_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping created successfully",
            "data": {
                "mapping": VehicleClusterMappingResponse(**new_mapping)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@vc_router.put("/{mapping_id}", response_model=Dict[str, Any])
async def update_vc_mapping(mapping_id: str, mapping_in: VehicleClusterMappingUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_mapping = await vc_service.update(mapping_id, mapping_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping updated successfully",
            "data": {
                "mapping": VehicleClusterMappingResponse(**updated_mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@vc_router.delete("/{mapping_id}", response_model=Dict[str, Any])
async def delete_vc_mapping(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await vc_service.delete(mapping_id)
        return {
            "success": True,
            "message": "Mapping deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@vc_router.get("/{mapping_id}", response_model=Dict[str, Any])
async def get_vc_mapping_by_id(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        mapping = await vc_service.get_by_id(mapping_id)
        return {
            "success": True,
            "message": "Mapping retrieved successfully",
            "data": {
                "mapping": VehicleClusterMappingResponse(**mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@vc_router.get("", response_model=Dict[str, Any])
async def get_vc_mapping_list(
    vehicleId: Optional[str] = Query(None),
    clusterId: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if vehicleId is not None:
        query["VehicleId"] = vehicleId
    if clusterId is not None:
        query["ClusterId"] = clusterId
    if isActive is not None:
        query["IsActive"] = isActive
        
    docs, total = await vc_service.get_list(query, skip, limit)
    serialized = [VehicleClusterMappingResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Mappings retrieved successfully",
        "data": {
            "mappings": serialized,
            "count": total
        }
    }
