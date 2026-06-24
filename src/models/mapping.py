from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Cluster-SubCluster Mapping
class ClusterSubClusterMappingCreate(BaseModel):
    ClusterId: str = Field(..., min_length=1, description="Cluster ID")
    SubClusterId: str = Field(..., min_length=1, description="Sub-cluster ID")
    IsActive: bool = Field(True, description="Active status")

class ClusterSubClusterMappingUpdate(BaseModel):
    ClusterId: Optional[str] = Field(None, min_length=1, description="Cluster ID")
    SubClusterId: Optional[str] = Field(None, min_length=1, description="Sub-cluster ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class ClusterSubClusterMappingResponse(BaseModel):
    MappingId: str
    ClusterId: str
    SubClusterId: str
    IsActive: bool
    CreatedBy: Optional[str] = None
    CreatedDate: datetime
    UpdatedBy: Optional[str] = None
    UpdatedDate: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


# Vehicle-Cluster Mapping
class VehicleClusterMappingCreate(BaseModel):
    VehicleId: str = Field(..., min_length=1, description="Vehicle ID")
    ClusterId: str = Field(..., min_length=1, description="Cluster ID")
    IsActive: bool = Field(True, description="Active status")

class VehicleClusterMappingUpdate(BaseModel):
    VehicleId: Optional[str] = Field(None, min_length=1, description="Vehicle ID")
    ClusterId: Optional[str] = Field(None, min_length=1, description="Cluster ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleClusterMappingResponse(BaseModel):
    MappingId: str
    VehicleId: str
    ClusterId: str
    IsActive: bool
    CreatedBy: Optional[str] = None
    CreatedDate: datetime
    UpdatedBy: Optional[str] = None
    UpdatedDate: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


# Vehicle-SubCluster Mapping
class VehicleSubClusterMappingCreate(BaseModel):
    VehicleId: str = Field(..., min_length=1, description="Vehicle ID")
    SubClusterId: str = Field(..., min_length=1, description="Sub-cluster ID")
    IsActive: bool = Field(True, description="Active status")

class VehicleSubClusterMappingUpdate(BaseModel):
    VehicleId: Optional[str] = Field(None, min_length=1, description="Vehicle ID")
    SubClusterId: Optional[str] = Field(None, min_length=1, description="Sub-cluster ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleSubClusterMappingResponse(BaseModel):
    MappingId: str
    VehicleId: str
    SubClusterId: str
    IsActive: bool
    CreatedBy: Optional[str] = None
    CreatedDate: datetime
    UpdatedBy: Optional[str] = None
    UpdatedDate: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
