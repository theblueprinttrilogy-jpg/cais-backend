"""
Analysis API Endpoints

This module provides endpoints for document analysis and processing.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.document import Document
from app.models.violation import Violation
from app.models.user import User
from app.schemas.analysis import AnalysisStatus, AnalysisResult, ViolationResponse
from app.api.deps import get_current_active_user
from app.agents.plan_inspector import PlanInspector
from app.agents.code_matcher import CodeMatcher
from app.agents.report_generator import ReportGenerator

router = APIRouter()


@router.get("/{task_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the status of an analysis task.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    # Get violations count
    violations_count = db.query(Violation).filter(
        Violation.document_id == document.id
    ).count()

    return {
        "task_id": task_id,
        "status": document.status,
        "progress": 100 if document.status == "completed" else 50,
        "violations_found": violations_count,
        "pages_processed": document.pages or 0,
        "created_at": document.created_at,
        "updated_at": document.updated_at
    }


@router.get("/{task_id}/results", response_model=AnalysisResult)
async def get_analysis_results(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the results of an analysis task.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    violations = db.query(Violation).filter(
        Violation.document_id == document.id
    ).all()

    return {
        "task_id": task_id,
        "document_id": str(document.id),
        "status": document.status,
        "total_violations": len(violations),
        "violations": [
            {
                "id": str(v.id),
                "type": v.violation_type,
                "severity": v.severity,
                "description": v.description,
                "code_reference": v.code_reference,
                "page_num": v.page_num,
                "evidence_path": v.evidence_path,
                "status": v.status
            }
            for v in violations
        ],
        "language": document.language,
        "pages": document.pages or 0,
        "completed_at": document.updated_at
    }


@router.post("/{task_id}/start")
async def start_analysis(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start or restart analysis for a document.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    if document.status == "processing":
        raise HTTPException(status_code=400, detail="Analysis already in progress")

    # Reset document status
    document.status = "processing"
    db.commit()

    # TODO: Start background task for analysis
    # This would call PlanInspector, CodeMatcher, and ReportGenerator

    return {
        "status": "started",
        "task_id": task_id,
        "message": "Analysis started. Check /status for progress."
    }
