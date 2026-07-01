from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class VehicleTypeCreate(BaseModel):
    VehicleTypeCode: str = Field(..., min_length=1, description="Unique vehicle type code")
    VehicleTypeName: str = Field(..., min_length=1, description="Vehicle type name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Vehicle type description")
    IsActive: bool = Field(True, description="Active status")

class VehicleTypeUpdate(BaseModel):
    VehicleTypeName: Optional[str] = Field(None, min_length=1, description="Vehicle type name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Vehicle type description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleTypeResponse(BaseModel):
    VehicleTypeId: str
    VehicleTypeCode: str
    VehicleTypeName: str
    WorkZoneId: ObjectIdStr
    Description: Optional[str] = None
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
