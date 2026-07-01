from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr
from src.models.supplier import SupplierVehicleCount  # shared vehicle-count item

# Supplier-Cluster Mapping
class SupplierClusterMappingCreate(BaseModel):
    SupplierId: ObjectIdStr = Field(..., description="Supplier ID")
    ClusterId: ObjectIdStr = Field(..., description="Cluster ID")
    IsActive: bool = Field(True, description="Active status")

class SupplierClusterMappingUpdate(BaseModel):
    SupplierId: Optional[ObjectIdStr] = Field(None, description="Supplier ID")
    ClusterId: Optional[ObjectIdStr] = Field(None, description="Cluster ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class SupplierClusterMappingResponse(BaseModel):
    MappingId: ObjectIdStr
    SupplierId: ObjectIdStr
    ClusterId: ObjectIdStr
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


# Vehicle-Supplier Mapping
class VehicleSupplierMappingCreate(BaseModel):
    VehicleId: ObjectIdStr = Field(..., description="Vehicle ID")
    SupplierId: ObjectIdStr = Field(..., description="Supplier ID")
    IsActive: bool = Field(True, description="Active status")

class VehicleSupplierMappingUpdate(BaseModel):
    VehicleId: Optional[ObjectIdStr] = Field(None, description="Vehicle ID")
    SupplierId: Optional[ObjectIdStr] = Field(None, description="Supplier ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleSupplierMappingResponse(BaseModel):
    MappingId: ObjectIdStr
    VehicleId: ObjectIdStr
    SupplierId: ObjectIdStr
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
    VehicleId: ObjectIdStr = Field(..., description="Vehicle ID")
    ClusterId: ObjectIdStr = Field(..., description="Cluster ID")
    IsActive: bool = Field(True, description="Active status")

class VehicleClusterMappingUpdate(BaseModel):
    VehicleId: Optional[ObjectIdStr] = Field(None, description="Vehicle ID")
    ClusterId: Optional[ObjectIdStr] = Field(None, description="Cluster ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleClusterMappingResponse(BaseModel):
    MappingId: ObjectIdStr
    VehicleId: ObjectIdStr
    ClusterId: ObjectIdStr
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


# BMC-Supplier-Cluster Mapping
class BMCSupplierClusterMappingCreate(BaseModel):
    BMCId: ObjectIdStr = Field(..., description="BMC ID")
    SupplierId: ObjectIdStr = Field(..., description="Supplier ID")
    ClusterId: ObjectIdStr = Field(..., description="Cluster ID")
    Vehicles: List[SupplierVehicleCount] = Field(default_factory=list, description="Array of vehicle ID and count")
    IsActive: bool = Field(True, description="Active status")

class BMCSupplierClusterMappingUpdate(BaseModel):
    BMCId: Optional[ObjectIdStr] = Field(None, description="BMC ID")
    SupplierId: Optional[ObjectIdStr] = Field(None, description="Supplier ID")
    ClusterId: Optional[ObjectIdStr] = Field(None, description="Cluster ID")
    Vehicles: Optional[List[SupplierVehicleCount]] = Field(None, description="Array of vehicle ID and count")
    IsActive: Optional[bool] = Field(None, description="Active status")

class BMCSupplierClusterMappingResponse(BaseModel):
    MappingId: ObjectIdStr
    BMCId: ObjectIdStr
    SupplierId: ObjectIdStr
    ClusterId: ObjectIdStr
    Vehicles: List[SupplierVehicleCount] = []
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
