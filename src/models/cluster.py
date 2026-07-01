from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class ClusterCreate(BaseModel):
    ClusterCode: str = Field(..., min_length=1, description="Unique cluster code")
    ClusterName: str = Field(..., min_length=1, description="Cluster name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Cluster description")
    IsActive: bool = Field(True, description="Active status")

class ClusterUpdate(BaseModel):
    ClusterName: Optional[str] = Field(None, min_length=1, description="Cluster name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Cluster description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class ClusterResponse(BaseModel):
    ClusterId: ObjectIdStr
    ClusterCode: str
    ClusterName: str
    WorkZoneId: Optional[ObjectIdStr] = None
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
