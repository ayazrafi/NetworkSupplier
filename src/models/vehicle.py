from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class VehicleCreate(BaseModel):
    VehicleType: str = Field(..., min_length=1, description="Vehicle type, e.g., 10 L, 12 L")
    VehicleCapacity: float = Field(..., gt=0, description="Capacity value")
    CapacityUnit: str = Field("L", description="Unit of capacity, default L")
    Description: Optional[str] = Field(None, description="Vehicle description")
    IsActive: bool = Field(True, description="Active status")

class VehicleUpdate(BaseModel):
    VehicleType: Optional[str] = Field(None, min_length=1, description="Vehicle type")
    VehicleCapacity: Optional[float] = Field(None, gt=0, description="Capacity value")
    CapacityUnit: Optional[str] = Field(None, description="Unit of capacity")
    Description: Optional[str] = Field(None, description="Vehicle description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class VehicleResponse(BaseModel):
    VehicleId: str
    VehicleType: str
    VehicleCapacity: float
    CapacityUnit: str
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
