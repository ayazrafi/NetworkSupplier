from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class OptimizationResultResponse(BaseModel):
    SupplierCode: str
    PlantCode: str
    TotalDistance: float
    TotalVehicleCount: int
    MilkTypeCode: str
    TotalSupply: float
    TotalDemand: float
