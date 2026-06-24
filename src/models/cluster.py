from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ClusterCreate(BaseModel):
    ClusterCode: str = Field(..., min_length=1, description="Unique cluster code")
    ClusterName: str = Field(..., min_length=1, description="Cluster name")
    Description: Optional[str] = Field(None, description="Cluster description")
    IsActive: bool = Field(True, description="Active status")

class ClusterUpdate(BaseModel):
    ClusterName: Optional[str] = Field(None, min_length=1, description="Cluster name")
    Description: Optional[str] = Field(None, description="Cluster description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class ClusterResponse(BaseModel):
    ClusterId: str
    ClusterCode: str
    ClusterName: str
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
