"""
Report Schemas - Pydantic Models for Report Endpoints

This module contains Pydantic schemas for Forensic Facts Dossier reports.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ReportResponse(BaseModel):
    """Report response schema."""
    id: str
    document_id: str
    file_path: str
    language: str
    download_count: int
    generated_at: datetime

    class Config:
        from_attributes = True


class ReportStatusResponse(BaseModel):
    """Report status response schema."""
    task_id: str
    status: str
    download_count: Optional[int] = None
    language: Optional[str] = None
    generated_at: Optional[datetime] = None
    file_path: Optional[str] = None
    message: Optional[str] = None


class ReportDownloadResponse(BaseModel):
    """Report download response schema."""
    task_id: str
    filename: str
    download_url: str
    expires_at: datetime
