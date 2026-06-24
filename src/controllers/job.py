from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
import os
from src.models.job import JobCreate, JobResponse
from src.services.job import JobService
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/jobs", tags=["Optimizer Jobs"])
job_service = JobService()

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_job(job_in: JobCreate, current_user: dict = Depends(get_current_user)):
    new_job = await job_service.create(job_in.model_dump(), current_user["userId"])
    return {
        "success": True,
        "message": "Job created successfully",
        "data": {
            "job": JobResponse(**new_job)
        }
    }

@router.post("/upload", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def upload_excel_file(
    JobName: str = Form(..., description="Name of the job"),
    file: UploadFile = File(..., description="Excel spreadsheet file (.xlsx)"),
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed.")
        
    content = await file.read()
    filepath = await job_service.save_uploaded_file(file.filename, content)
    
    job_data = {
        "JobName": JobName,
        "UploadedFileName": file.filename,
        "UploadedFilePath": filepath
    }
    
    new_job = await job_service.create(job_data, current_user["userId"])
    return {
        "success": True,
        "message": "Excel file uploaded and job queued successfully.",
        "data": {
            "job": JobResponse(**new_job)
        }
    }

@router.get("/pending", response_model=Dict[str, Any])
async def get_pending_jobs(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1), current_user: dict = Depends(get_current_user)):
    docs, total = await job_service.get_list({"JobStatus": "Pending"}, skip, limit)
    serialized = [JobResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Pending jobs retrieved successfully",
        "data": {
            "jobs": serialized,
            "count": total
        }
    }

@router.get("/processing", response_model=Dict[str, Any])
async def get_processing_jobs(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1), current_user: dict = Depends(get_current_user)):
    docs, total = await job_service.get_list({"JobStatus": "InProgress"}, skip, limit)
    serialized = [JobResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Processing jobs retrieved successfully",
        "data": {
            "jobs": serialized,
            "count": total
        }
    }

@router.get("/completed", response_model=Dict[str, Any])
async def get_completed_jobs(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1), current_user: dict = Depends(get_current_user)):
    docs, total = await job_service.get_list({"JobStatus": "Completed"}, skip, limit)
    serialized = [JobResponse(**item) for item in docs]
    return {
        "success": True,
        "message": "Completed jobs retrieved successfully",
        "data": {
            "jobs": serialized,
            "count": total
        }
    }

@router.get("/{job_id}/download", status_code=status.HTTP_200_OK)
async def download_result_file(job_id: str, current_user: dict = Depends(get_current_user)):
    try:
        job = await job_service.get_by_id(job_id)
        if job["JobStatus"] != "Completed":
            raise HTTPException(status_code=400, detail=f"Job is not completed yet (status: {job['JobStatus']})")
            
        result_path = job.get("ResultFilePath")
        if not result_path or not os.path.exists(result_path):
            raise HTTPException(status_code=404, detail="Result file not found on server.")
            
        return FileResponse(
            path=result_path,
            filename=f"network_results_{job_id[:8]}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{job_id}", response_model=Dict[str, Any])
async def delete_job(job_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await job_service.delete(job_id)
        return {
            "success": True,
            "message": "Job deleted successfully",
            "data": None
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job_by_id(job_id: str, current_user: dict = Depends(get_current_user)):
    try:
        job = await job_service.get_by_id(job_id)
        return {
            "success": True,
            "message": "Job retrieved successfully",
            "data": {
                "job": JobResponse(**job)
            }
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=Dict[str, Any])
async def get_job_list(
    status: Optional[str] = Query(None, description="Filter by JobStatus"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    sortBy: str = Query("CreatedDate"),
    sortOrder: str = Query("desc", description="asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status is not None:
        query["JobStatus"] = status
        
    s_order = -1 if sortOrder.lower() == "desc" else 1
    docs, total = await job_service.get_list(query, skip, limit, sortBy, s_order)
    serialized = [JobResponse(**item) for item in docs]
    
    return {
        "success": True,
        "message": "Job list retrieved successfully",
        "data": {
            "jobs": serialized,
            "count": total
        }
    }
