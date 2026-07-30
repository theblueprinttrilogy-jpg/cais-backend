"""
Analysis Schemas - Pydantic Models for Analysis Endpoints

This module contains Pydantic schemas for document analysis.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ViolationResponse(BaseModel):
    """Violation response schema."""
    id: str
    type: str
    severity: str
    description: str
    code_reference: Optional[str] = None
    page_num: Optional[int] = None
    evidence_path: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class AnalysisStatus(BaseModel):
    """Analysis status response schema."""
    task_id: str
    status: str
    progress: int
    violations_found: int
    pages_processed: int
    created_at: datetime
    updated_at: datetime


class AnalysisResult(BaseModel):
    """Analysis results response schema."""
    task_id: str
    document_id: str
    status: str
    total_violations: int
    violations: List[ViolationResponse]
    language: str
    pages: int
    completed_at: Optional[datetime] = None


class AnalysisStartRequest(BaseModel):
    """Analysis start request schema."""
    task_id: str


class AnalysisStartResponse(BaseModel):
    """Analysis start response schema."""
    status: str
    task_id: str
    message: str
