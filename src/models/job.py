from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class JobCreate(BaseModel):
    JobName: str = Field(..., min_length=1, description="Job name")

class JobResponse(BaseModel):
    JobId: str
    JobName: str
    UploadedFileName: Optional[str] = None
    UploadedFilePath: Optional[str] = None
    JobStatus: str  # Pending, InProgress, Completed, Failed
    TotalRecords: int = 0
    ProcessedRecords: int = 0
    ResultFilePath: Optional[str] = None
    ErrorMessage: Optional[str] = None
    CreatedBy: Optional[str] = None
    CreatedDate: datetime
    StartedDate: Optional[datetime] = None
    CompletedDate: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
