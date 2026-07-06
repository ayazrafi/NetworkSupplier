from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
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

@router.get("/{jobId}/result", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_request_result(jobId: str):
    try:
        from src.repositories.result import OptimizationResultsRepository
        repo = OptimizationResultsRepository()
        
        # Get all results matching this jobId
        results = await repo.collection.find({"JobId": jobId}).to_list(length=None)
        
        # Clean _id for serialization
        for r in results:
            if "_id" in r:
                r["_id"] = str(r["_id"])
                
        return {
            "success": True,
            "message": "Results fetched successfully",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
