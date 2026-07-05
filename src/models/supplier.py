from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class SupplierVehicleCount(BaseModel):
    vehicleId: ObjectIdStr = Field(..., description="Vehicle ID")
    count: int = Field(..., ge=0, description="Vehicle count")

class SupplierCreate(BaseModel):
    SupplierCode: str = Field(..., min_length=1, description="Unique supplier code")
    SupplierName: str = Field(..., min_length=1, description="Supplier name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    shortName: Optional[str] = Field(None, description="Supplier short name")
    Description: Optional[str] = Field(None, description="Supplier description")
    Vehicles: Optional[List[SupplierVehicleCount]] = Field(default_factory=list, description="Allocated vehicles with counts")
    IsActive: bool = Field(True, description="Active status")

class SupplierUpdate(BaseModel):
    SupplierName: Optional[str] = Field(None, min_length=1, description="Supplier name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    shortName: Optional[str] = Field(None, description="Supplier short name")
    Description: Optional[str] = Field(None, description="Supplier description")
    Vehicles: Optional[List[SupplierVehicleCount]] = Field(None, description="Allocated vehicles with counts")
    IsActive: Optional[bool] = Field(None, description="Active status")

class SupplierResponse(BaseModel):
    SupplierId: ObjectIdStr
    SupplierCode: str
    SupplierName: str
    WorkZoneId: Optional[ObjectIdStr] = None
    shortName: Optional[str] = None
    Description: Optional[str] = None
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
