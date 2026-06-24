import os
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional
from src.repositories.job import JobRepository

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

class JobService:
    def __init__(self):
        self.repository = JobRepository()

    async def create(self, job_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        job_id = str(uuid.uuid4())
        job_data["JobId"] = job_id
        job_data["JobStatus"] = "Pending"
        job_data["TotalRecords"] = 0
        job_data["ProcessedRecords"] = 0
        job_data["CreatedBy"] = created_by
        job_data["CreatedDate"] = now
        # Optional fields
        job_data["UploadedFileName"] = job_data.get("UploadedFileName")
        job_data["UploadedFilePath"] = job_data.get("UploadedFilePath")
        job_data["ResultFilePath"] = None
        job_data["ErrorMessage"] = None
        job_data["StartedDate"] = None
        job_data["CompletedDate"] = None

        return await self.repository.create(job_data)

    async def update(self, job_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("JobId", job_id)
        if not existing:
            raise KeyError(f"Job with ID '{job_id}' not found.")
        
        updated_doc = await self.repository.update("JobId", job_id, update_data)
        if not updated_doc:
            raise RuntimeError("Failed to update job record.")
        return updated_doc

    async def delete(self, job_id: str) -> bool:
        existing = await self.repository.get_by_id("JobId", job_id)
        if not existing:
            raise KeyError(f"Job with ID '{job_id}' not found.")
        
        # Clean up files from disk if they exist
        if existing.get("UploadedFilePath") and os.path.exists(existing["UploadedFilePath"]):
            try:
                os.remove(existing["UploadedFilePath"])
            except OSError:
                pass
        if existing.get("ResultFilePath") and os.path.exists(existing["ResultFilePath"]):
            try:
                os.remove(existing["ResultFilePath"])
            except OSError:
                pass

        return await self.repository.delete("JobId", job_id)

    async def get_by_id(self, job_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("JobId", job_id)
        if not existing:
            raise KeyError(f"Job with ID '{job_id}' not found.")
        return existing

    async def get_list(
        self, 
        query: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 10, 
        sort_by: str = "CreatedDate", 
        sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repository.get_list(query, skip, limit, sort_by, sort_order)

    async def save_uploaded_file(self, filename: str, content: bytes) -> str:
        # Create a unique filename to prevent collision
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(UPLOAD_DIR, unique_name)
        with open(filepath, "wb") as f:
            f.write(content)
        return filepath
