from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SubClusterCreate(BaseModel):
    ClusterId: str = Field(..., min_length=1, description="Parent cluster ID")
    SubClusterCode: str = Field(..., min_length=1, description="Unique sub-cluster code")
    SubClusterName: str = Field(..., min_length=1, description="Sub-cluster name")
    Description: Optional[str] = Field(None, description="Sub-cluster description")
    IsActive: bool = Field(True, description="Active status")

class SubClusterUpdate(BaseModel):
    ClusterId: Optional[str] = Field(None, min_length=1, description="Parent cluster ID")
    SubClusterName: Optional[str] = Field(None, min_length=1, description="Sub-cluster name")
    Description: Optional[str] = Field(None, description="Sub-cluster description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class SubClusterResponse(BaseModel):
    SubClusterId: str
    ClusterId: str
    SubClusterCode: str
    SubClusterName: str
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
