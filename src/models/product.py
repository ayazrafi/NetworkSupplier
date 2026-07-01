from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.models.validators import ObjectIdStr


class ProductCreate(BaseModel):
    ProductCode: str = Field(..., min_length=1, description="Unique product code")
    ProductName: str = Field(..., min_length=1, description="Product name")
    WorkZoneId: ObjectIdStr = Field(..., description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Product description")
    IsActive: bool = Field(True, description="Active status")


class ProductUpdate(BaseModel):
    ProductName: Optional[str] = Field(None, min_length=1, description="Product name")
    WorkZoneId: Optional[ObjectIdStr] = Field(None, description="Associated work zone ID")
    Description: Optional[str] = Field(None, description="Product description")
    IsActive: Optional[bool] = Field(None, description="Active status")


class ProductResponse(BaseModel):
    ProductId: ObjectIdStr
    ProductCode: str
    ProductName: str
    WorkZoneId: ObjectIdStr
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
