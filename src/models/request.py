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

class RequestPlantSupplierMappingInput(BaseModel):
    plantCode: str
    supplierCode: str
    productCode: str

class BmcMinQuantitySupplyInput(BaseModel):
    product: str
    value: float

class PlantFixedDemandInput(BaseModel):
    product: str
    type: str
    plantCode: str
    value: float

class RequestConstraintInput(BaseModel):
    supplierCode: str
    isLenient: Optional[bool] = None
    bmcMinQuantitySupply: Optional[BmcMinQuantitySupplyInput] = None
    plantFixedDemand: Optional[PlantFixedDemandInput] = None

class RequestProductConfigurationInput(BaseModel):
    product: str
    derivedFrom: str
    canBeConvert: str

class RequestCreateInput(BaseModel):
    requestName: str
    plants: List[RequestPlantInput]
    mmcs: List[RequestMMCInput]
    vehicles: List[RequestVehicleInput] = Field(..., validation_alias="vechicles")
    plantSupplierMapping: List[RequestPlantSupplierMappingInput]
    maxDistance: int
    leaveQuantity: int = 0
    constraints: Optional[List[RequestConstraintInput]] = []
    productConfiguration: Optional[List[RequestProductConfigurationInput]] = []

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
