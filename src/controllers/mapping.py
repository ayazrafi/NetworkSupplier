from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from src.models.mapping import (
    ClusterSubClusterMappingCreate, ClusterSubClusterMappingUpdate, ClusterSubClusterMappingResponse,
    VehicleClusterMappingCreate, VehicleClusterMappingUpdate, VehicleClusterMappingResponse,
    VehicleSubClusterMappingCreate, VehicleSubClusterMappingUpdate, VehicleSubClusterMappingResponse
)
from src.services.mapping import (
    ClusterSubClusterMappingService,
    VehicleClusterMappingService,
    VehicleSubClusterMappingService
)
from src.middlewares.auth import get_current_user

# 1. Cluster-SubCluster Router
csc_router = APIRouter(prefix="/api/v1/cluster-subcluster-mapping", tags=["Cluster-SubCluster Mapping"])
csc_service = ClusterSubClusterMappingService()

@csc_router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_csc_mapping(mapping_in: ClusterSubClusterMappingCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_mapping = await csc_service.create(mapping_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping created successfully",
            "data": {
                "mapping": ClusterSubClusterMappingResponse(**new_mapping)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@csc_router.put("/{mapping_id}", response_model=Dict[str, Any])
async def update_csc_mapping(mapping_id: str, mapping_in: ClusterSubClusterMappingUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_mapping = await csc_service.update(mapping_id, mapping_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping updated successfully",
            "data": {
                "mapping": ClusterSubClusterMappingResponse(**updated_mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@csc_router.delete("/{mapping_id}", response_model=Dict[str, Any])
async def delete_csc_mapping(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await csc_service.delete(mapping_id)
        return {
            "success": True,
            "message": "Mapping deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@csc_router.get("/{mapping_id}", response_model=Dict[str, Any])
async def get_csc_mapping_by_id(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        mapping = await csc_service.get_by_id(mapping_id)
        return {
            "success": True,
            "message": "Mapping retrieved successfully",
            "data": {
                "mapping": ClusterSubClusterMappingResponse(**mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@csc_router.get("", response_model=Dict[str, Any])
async def get_csc_mapping_list(
    clusterId: Optional[str] = Query(None),
    subClusterId: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if clusterId is not None:
        query["ClusterId"] = clusterId
    if subClusterId is not None:
        query["SubClusterId"] = subClusterId
    if isActive is not None:
        query["IsActive"] = isActive
        
    docs, total = await csc_service.get_list(query, skip, limit)
    serialized = [ClusterSubClusterMappingResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Mappings retrieved successfully",
        "data": {
            "mappings": serialized,
            "count": total
        }
    }


# 2. Vehicle-Cluster Router
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


# 3. Vehicle-SubCluster Router
vsc_router = APIRouter(prefix="/api/v1/vehicle-subcluster-mapping", tags=["Vehicle-SubCluster Mapping"])
vsc_service = VehicleSubClusterMappingService()

@vsc_router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_vsc_mapping(mapping_in: VehicleSubClusterMappingCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_mapping = await vsc_service.create(mapping_in.model_dump(), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping created successfully",
            "data": {
                "mapping": VehicleSubClusterMappingResponse(**new_mapping)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@vsc_router.put("/{mapping_id}", response_model=Dict[str, Any])
async def update_vsc_mapping(mapping_id: str, mapping_in: VehicleSubClusterMappingUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated_mapping = await vsc_service.update(mapping_id, mapping_in.model_dump(exclude_unset=True), current_user["userId"])
        return {
            "success": True,
            "message": "Mapping updated successfully",
            "data": {
                "mapping": VehicleSubClusterMappingResponse(**updated_mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@vsc_router.delete("/{mapping_id}", response_model=Dict[str, Any])
async def delete_vsc_mapping(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await vsc_service.delete(mapping_id)
        return {
            "success": True,
            "message": "Mapping deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@vsc_router.get("/{mapping_id}", response_model=Dict[str, Any])
async def get_vsc_mapping_by_id(mapping_id: str, current_user: dict = Depends(get_current_user)):
    try:
        mapping = await vsc_service.get_by_id(mapping_id)
        return {
            "success": True,
            "message": "Mapping retrieved successfully",
            "data": {
                "mapping": VehicleSubClusterMappingResponse(**mapping)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@vsc_router.get("", response_model=Dict[str, Any])
async def get_vsc_mapping_list(
    vehicleId: Optional[str] = Query(None),
    subClusterId: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if vehicleId is not None:
        query["VehicleId"] = vehicleId
    if subClusterId is not None:
        query["SubClusterId"] = subClusterId
    if isActive is not None:
        query["IsActive"] = isActive
        
    docs, total = await vsc_service.get_list(query, skip, limit)
    serialized = [VehicleSubClusterMappingResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Mappings retrieved successfully",
        "data": {
            "mappings": serialized,
            "count": total
        }
    }
