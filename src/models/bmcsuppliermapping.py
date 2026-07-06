from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr

class BMCSupplierMappingCreate(BaseModel):
    BMCCode: str = Field(..., min_length=1, description="BMC code")
    SupplierCode: str = Field(..., min_length=1, description="Supplier code")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    IsActive: bool = Field(True, description="Active status")

class BMCSupplierMappingUpdate(BaseModel):
    BMCCode: Optional[str] = Field(None, min_length=1, description="BMC code")
    SupplierCode: Optional[str] = Field(None, min_length=1, description="Supplier code")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    IsActive: Optional[bool] = Field(None, description="Active status")

class BMCSupplierMappingResponse(BaseModel):
    BMCSupplierMappingId: ObjectIdStr
    BMCCode: str
    SupplierCode: str
    WorkZoneId: Optional[ObjectIdStr] = None
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
