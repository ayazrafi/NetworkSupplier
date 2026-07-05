from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class SupplierPriorityCreate(BaseModel):
    PlantCode: str = Field(..., min_length=1, description="Plant code")
    SupplierCode: str = Field(..., min_length=1, description="Supplier code")
    ProductCode: str = Field(..., min_length=1, description="Product code")
    IsActive: bool = Field(True, description="Active status")

class SupplierPriorityUpdate(BaseModel):
    PlantCode: Optional[str] = Field(None, min_length=1, description="Plant code")
    SupplierCode: Optional[str] = Field(None, min_length=1, description="Supplier code")
    ProductCode: Optional[str] = Field(None, min_length=1, description="Product code")
    IsActive: Optional[bool] = Field(None, description="Active status")

class SupplierPriorityResponse(BaseModel):
    SupplierPriorityId: ObjectIdStr
    PlantCode: str
    SupplierCode: str
    ProductCode: str
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
