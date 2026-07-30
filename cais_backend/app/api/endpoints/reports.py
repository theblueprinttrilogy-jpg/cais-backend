"""
Reports API Endpoints

This module provides endpoints for downloading and viewing Forensic Facts Dossier.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.db.models import Document, Report, User
from app.api.deps import get_current_active_user

router = APIRouter()


@router.get("/{task_id}/download")
async def download_report(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download the Forensic Facts Dossier PDF.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        raise NotFoundException("Report", task_id)

    # Increment download count
    report.download_count += 1
    db.commit()

    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=f"forensic_dossier_{task_id}.pdf"
    )


@router.get("/{task_id}/view")
async def view_report(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    View the Forensic Facts Dossier in browser.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        raise NotFoundException("Report", task_id)

    # Increment download count
    report.download_count += 1
    db.commit()

    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=f"forensic_dossier_{task_id}.pdf"
    )


@router.get("/{task_id}/status")
async def get_report_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the status of a report generation.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Report not yet generated"
        }

    return {
        "task_id": task_id,
        "status": "completed",
        "download_count": report.download_count,
        "language": report.language,
        "generated_at": report.generated_at,
        "file_path": report.file_path
    }
