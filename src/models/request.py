from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class RequestPlantInput(BaseModel):
    plantCode: str
    product: str
    demand: float

class RequestMMCInput(BaseModel):
    mmcCode: str
    supplierCode: str
    product: str
    supply: float

class RequestVehicleInput(BaseModel):
    supplierCode: str
    vehicleType: str
    count: int

class RequestCreateInput(BaseModel):
    requestName: str
    plants: List[RequestPlantInput]
    mmcs: List[RequestMMCInput]
    vehicles: List[RequestVehicleInput] = Field(..., validation_alias="vechicles")
    maxDistance: int
    leaveQuantity: int = 0

class OptimizationRequestResponse(BaseModel):
    requestId: str
    requestName: str
    status: str
    createdBy: str
    createdOn: datetime
    startedOn: Optional[datetime] = None
    completedOn: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
