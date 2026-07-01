from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class WorkZoneCreate(BaseModel):
    WorkZoneCode: str = Field(..., min_length=1, description="Unique work zone code")
    WorkZoneName: str = Field(..., min_length=1, description="Work zone name")
    OrganizationId: ObjectIdStr = Field(..., description="Associated organization ID")
    Description: Optional[str] = Field(None, description="Work zone description")
    IsActive: bool = Field(True, description="Active status")

class WorkZoneUpdate(BaseModel):
    WorkZoneName: Optional[str] = Field(None, min_length=1, description="Work zone name")
    OrganizationId: Optional[ObjectIdStr] = Field(None, description="Associated organization ID")
    Description: Optional[str] = Field(None, description="Work zone description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class WorkZoneResponse(BaseModel):
    WorkZoneId: ObjectIdStr
    WorkZoneCode: str
    WorkZoneName: str
    OrganizationId: ObjectIdStr
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
