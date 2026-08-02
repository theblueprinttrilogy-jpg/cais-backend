"""
Reports API Endpoints

This module provides endpoints for downloading and viewing Forensic Facts Dossier.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.db.models import Document, Report, User
from app.api.deps import get_current_active_user

router = APIRouter()


# ============================================================
# DOWNLOAD ENDPOINT (PUBLIC FOR TESTING)
# ============================================================

@router.get("/{task_id}/download")
async def download_report(
    task_id: str,
    db: Session = Depends(get_db)
    # Uncomment the line below to enable authentication
    # current_user: User = Depends(get_current_active_user),
):
    """
    Download the Forensic Facts Dossier PDF.

    This endpoint is temporarily public for testing purposes.
    To enable authentication, uncomment the current_user dependency.
    """
    # Get document
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    # Get report
    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        raise NotFoundException("Report", task_id)

    # Verify file exists
    if not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on disk"
        )

    # Increment download count
    report.download_count += 1
    db.commit()

    # Return file
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=f"forensic_dossier_{task_id}.pdf",
        headers={
            "Content-Disposition": f"attachment; filename=forensic_dossier_{task_id}.pdf"
        }
    )


# ============================================================
# VIEW ENDPOINT (PUBLIC FOR TESTING)
# ============================================================

@router.get("/{task_id}/view")
async def view_report(
    task_id: str,
    db: Session = Depends(get_db)
    # Uncomment the line below to enable authentication
    # current_user: User = Depends(get_current_active_user),
):
    """
    View the Forensic Facts Dossier in browser.

    This endpoint is temporarily public for testing purposes.
    To enable authentication, uncomment the current_user dependency.
    """
    # Get document
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    # Get report
    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        raise NotFoundException("Report", task_id)

    # Verify file exists
    if not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on disk"
        )

    # Increment download count
    report.download_count += 1
    db.commit()

    # Return file for inline viewing
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=f"forensic_dossier_{task_id}.pdf",
        headers={
            "Content-Disposition": f"inline; filename=forensic_dossier_{task_id}.pdf"
        }
    )


# ============================================================
# STATUS ENDPOINT
# ============================================================

@router.get("/{task_id}/status")
async def get_report_status(
    task_id: str,
    db: Session = Depends(get_db)
    # Uncomment the line below to enable authentication
    # current_user: User = Depends(get_current_active_user),
):
    """
    Get the status of a report generation.
    """
    # Get document
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    # Get report
    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Report not yet generated"
        }

    # Verify file exists
    file_exists = os.path.exists(report.file_path)
    file_size = os.path.getsize(report.file_path) if file_exists else 0

    return {
        "task_id": task_id,
        "status": "completed",
        "download_count": report.download_count,
        "language": report.language,
        "generated_at": report.generated_at,
        "file_path": report.file_path,
        "file_exists": file_exists,
        "file_size_bytes": file_size
    }


# ============================================================
# AUTHENTICATED VERSIONS (FOR PRODUCTION)
# ============================================================

# Uncomment the following functions and comment out the public ones
# to enable authentication in production.

# @router.get("/{task_id}/download")
# async def download_report_secure(
#     task_id: str,
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db)
# ):
#     document = db.query(Document).filter(Document.task_id == task_id).first()
#     if not document:
#         raise NotFoundException("Document", task_id)
#     report = db.query(Report).filter(Report.document_id == document.id).first()
#     if not report:
#         raise NotFoundException("Report", task_id)
#     if not os.path.exists(report.file_path):
#         raise HTTPException(status_code=404, detail="Report file not found")
#     report.download_count += 1
#     db.commit()
#     return FileResponse(
#         report.file_path,
#         media_type="application/pdf",
#         filename=f"forensic_dossier_{task_id}.pdf"
#     )


# ============================================================
# DEBUG ENDPOINT (OPTIONAL)
# ============================================================

@router.get("/{task_id}/debug")
async def debug_report(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check report file path and existence.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        return {"error": "Document not found"}

    report = db.query(Report).filter(Report.document_id == document.id).first()
    if not report:
        return {"error": "Report not found"}

    file_exists = os.path.exists(report.file_path)
    file_size = os.path.getsize(report.file_path) if file_exists else 0

    return {
        "task_id": task_id,
        "document_id": str(document.id),
        "report_id": str(report.id),
        "file_path": report.file_path,
        "file_exists": file_exists,
        "file_size_bytes": file_size,
        "language": report.language,
        "download_count": report.download_count,
        "generated_at": report.generated_at
    }
