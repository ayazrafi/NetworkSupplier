from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Supplier-Cluster Mapping
class SupplierClusterMappingCreate(BaseModel):
    SupplierId: str = Field(..., min_length=1, description="Supplier ID")
    ClusterId: str = Field(..., min_length=1, description="Cluster ID")
    IsActive: bool = Field(True, description="Active status")

class SupplierClusterMappingUpdate(BaseModel):
    SupplierId: Optional[str] = Field(None, min_length=1, description="Supplier ID")
    ClusterId: Optional[str] = Field(None, min_length=1, description="Cluster ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class SupplierClusterMappingResponse(BaseModel):
    MappingId: str
    SupplierId: str
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


# Vehicle-Supplier Mapping
class VehicleSupplierMappingCreate(BaseModel):
    VehicleId: str = Field(..., min_length=1, description="Vehicle ID")
    SupplierId: str = Field(..., min_length=1, description="Supplier ID")
    IsActive: bool = Field(True, description="Active status")

class VehicleSupplierMappingUpdate(BaseModel):
    VehicleId: Optional[str] = Field(None, min_length=1, description="Vehicle ID")
    SupplierId: Optional[str] = Field(None, min_length=1, description="Supplier ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleSupplierMappingResponse(BaseModel):
    MappingId: str
    VehicleId: str
    SupplierId: str
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
