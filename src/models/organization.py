from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class OrganizationCreate(BaseModel):
    OrganizationCode: str = Field(..., min_length=1, description="Unique organization code")
    OrganizationName: str = Field(..., min_length=1, description="Organization name")
    Description: Optional[str] = Field(None, description="Organization description")
    IsActive: bool = Field(True, description="Active status")

class OrganizationUpdate(BaseModel):
    OrganizationName: Optional[str] = Field(None, min_length=1, description="Organization name")
    Description: Optional[str] = Field(None, description="Organization description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class OrganizationResponse(BaseModel):
    OrganizationId: ObjectIdStr
    OrganizationCode: str
    OrganizationName: str
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
