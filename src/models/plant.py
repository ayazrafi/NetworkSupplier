from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class PlantCreate(BaseModel):
    PlantCode: str = Field(..., min_length=1, description="Unique plant code")
    PlantName: str = Field(..., min_length=1, description="Plant name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    Address: Optional[str] = Field(None, description="Physical address of the plant")
    Latitude: float = Field(..., description="Latitude coordinate")
    Longitude: float = Field(..., description="Longitude coordinate")
    Capacity: float = Field(..., gt=0, description="Plant capacity in Liters/day")
    IsActive: bool = Field(True, description="Active status")

class PlantUpdate(BaseModel):
    PlantName: Optional[str] = Field(None, min_length=1, description="Plant name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    Address: Optional[str] = Field(None, description="Physical address of the plant")
    Latitude: Optional[float] = Field(None, description="Latitude coordinate")
    Longitude: Optional[float] = Field(None, description="Longitude coordinate")
    Capacity: Optional[float] = Field(None, gt=0, description="Plant capacity")
    IsActive: Optional[bool] = Field(None, description="Active status")

class PlantResponse(BaseModel):
    PlantId: str
    PlantCode: str
    PlantName: str
    WorkZoneId: Optional[ObjectIdStr] = None
    Address: Optional[str] = None
    Latitude: float
    Longitude: float
    Capacity: float
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
