from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class SupplierCreate(BaseModel):
    SupplierCode: str = Field(..., min_length=1, description="Unique supplier code")
    SupplierName: str = Field(..., min_length=1, description="Supplier name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Supplier description")
    IsActive: bool = Field(True, description="Active status")

class SupplierUpdate(BaseModel):
    SupplierName: Optional[str] = Field(None, min_length=1, description="Supplier name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Supplier description")
    IsActive: Optional[bool] = Field(None, description="Active status")

class SupplierResponse(BaseModel):
    SupplierId: str
    SupplierCode: str
    SupplierName: str
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
