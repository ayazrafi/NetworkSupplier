from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime
from src.models.request import RequestCreateInput, OptimizationRequestResponse
from src.services.request import RequestService

router = APIRouter(prefix="/api/v1/request", tags=["Optimization Request"])
request_service = RequestService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_request(request_in: RequestCreateInput):
    try:
        created_by = "System"
        new_request = await request_service.create_request(request_in, created_by)
        return {
            "success": True,
            "message": "Optimization request created successfully",
            "data": {
                "request": OptimizationRequestResponse(**new_request)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_requests_by_date(start_date: datetime, end_date: datetime):
    try:
        requests = await request_service.get_requests_by_date_range(start_date, end_date)
        return {
            "success": True,
            "message": "Requests fetched successfully",
            "data": requests
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{jobId}/result", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_request_result(jobId: str):
    try:
        
        jobId='REQ0046'
        from src.repositories.result import OptimizerRequestResultRepository
        repo = OptimizerRequestResultRepository()
        
        # Get the result matching this jobId
        result = await repo.collection.find_one({"jobId": jobId})
        
        # Clean _id for serialization
        if result and "_id" in result:
            result["_id"] = str(result["_id"])
                
        return {
            "success": True,
            "message": "Result fetched successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
