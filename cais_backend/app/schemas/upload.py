"""
CAIS Code Compliance - Upload Schemas

Pydantic models for document upload and job status responses.
"""

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, UUID4


class UploadResponse(BaseModel):
    """Response model for document upload endpoint."""
    job_id: str
    document_id: str
    status: str
    message: str
    timestamp: datetime = datetime.utcnow()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobStatusResponse(BaseModel):
    """Response model for job status retrieval."""
    job_id: str
    status: str  # queued, processing, completed, failed
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
