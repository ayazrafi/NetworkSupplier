from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class BMCCreate(BaseModel):
    BMCCode: str = Field(..., min_length=1, description="Unique BMC code")
    BMCName: str = Field(..., min_length=1, description="BMC name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    Address: Optional[str] = Field(None, description="Physical address of the BMC")
    Latitude: float = Field(..., description="Latitude coordinate")
    Longitude: float = Field(..., description="Longitude coordinate")
    ContactPerson: Optional[str] = Field(None, description="Contact person name")
    MobileNumber: Optional[str] = Field(None, description="Mobile phone number")
    IsActive: bool = Field(True, description="Active status")

class BMCUpdate(BaseModel):
    BMCName: Optional[str] = Field(None, min_length=1, description="BMC name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    Address: Optional[str] = Field(None, description="Physical address of the BMC")
    Latitude: Optional[float] = Field(None, description="Latitude coordinate")
    Longitude: Optional[float] = Field(None, description="Longitude coordinate")
    ContactPerson: Optional[str] = Field(None, description="Contact person name")
    MobileNumber: Optional[str] = Field(None, description="Mobile phone number")
    IsActive: Optional[bool] = Field(None, description="Active status")

class BMCResponse(BaseModel):
    BMCId: ObjectIdStr
    BMCCode: str
    BMCName: str
    WorkZoneId: Optional[ObjectIdStr] = None
    Address: Optional[str] = None
    Latitude: float
    Longitude: float
    ContactPerson: Optional[str] = None
    MobileNumber: Optional[str] = None
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
