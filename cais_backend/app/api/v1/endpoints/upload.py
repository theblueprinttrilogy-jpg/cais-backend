"""
CAIS Code Compliance - Upload Endpoint Module

Handles document upload, multi-agent pipeline orchestration,
and background processing for code compliance analysis.
"""

import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import User, Document, Project, Violation, Report, WORMLedgerEntry
from app.core.security import get_current_user
from app.services.pipeline import (
    PlanInspector,
    JurisdictionOrchestrator,
    CodeMatcher,
    ReportGenerator,
    WormLedger,
)
from app.schemas.upload import UploadResponse, JobStatusResponse
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# In-memory store for tracking background job status and results
# Structure: {job_id: {"status": str, "result": dict, "error": str, "updated_at": datetime}}
processing_jobs: Dict[str, Dict[str, Any]] = {}


def get_or_create_default_user(db: Session) -> User:
    """
    Get or create a default user for anonymous uploads.

    Returns:
        User: The default user instance.
    """
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    user = db.query(User).filter(User.id == default_user_id).first()
    if not user:
        user = User(
            id=default_user_id,
            email="default@cais.com",
            full_name="Default User",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created default user with ID: %s", default_user_id)
    return user


@router.post("/file", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    jurisdiction: str = Form(...),
    project_id: Optional[str] = Form(None),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for code compliance analysis.

    - **file**: The document to analyze (PDF, image, etc.)
    - **jurisdiction**: Legal jurisdiction for code references (e.g., "NYC", "CA")
    - **project_id**: Optional project ID to associate the document
    """
    # Use default user if no authenticated user
    if not user:
        user = get_or_create_default_user(db)

    # Validate file type and size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Generate unique identifiers
    document_id = uuid.uuid4()
    job_id = uuid.uuid4()

    # Save file to temporary storage (simulated)
    file_path = f"{settings.STORAGE_PATH}/{uuid.uuid4()}_{file.filename}"

    # Create document record
    document = Document(
        id=document_id,
        filename=file.filename,
        file_path=file_path,
        jurisdiction=jurisdiction,
        project_id=uuid.UUID(project_id) if project_id else None,
        user_id=user.id,
        status="pending",
        uploaded_at=datetime.utcnow(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Initialize in-memory job tracking
    processing_jobs[str(job_id)] = {
        "status": "queued",
        "result": None,
        "error": None,
        "updated_at": datetime.utcnow(),
    }

    # Schedule background processing
    background_tasks.add_task(
        process_document_async,
        document_id=document_id,
        job_id=job_id,
        file=file,
        jurisdiction=jurisdiction,
        project_id=project_id,
        db_session=db,  # Pass session to reuse (but careful: background task uses its own session)
    )

    return UploadResponse(
        job_id=str(job_id),
        document_id=str(document_id),
        status="queued",
        message="Document uploaded and queued for analysis.",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Retrieve the status of an analysis job.

    - **job_id**: UUID of the analysis job
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # First check in-memory store
    job_data = processing_jobs.get(job_id)
    if not job_data:
        # Fallback: query the document status from database
        document = db.query(Document).filter(Document.id == job_uuid).first()
        if not document:
            raise HTTPException(status_code=404, detail="Job not found")
        # Build a response from the document status
        return JobStatusResponse(
            job_id=job_id,
            status=document.status,
            result=None,
            error_message=None,
            updated_at=document.updated_at,
        )

    # Return from in-memory store
    return JobStatusResponse(
        job_id=job_id,
        status=job_data["status"],
        result=job_data["result"],
        error_message=job_data.get("error"),
        updated_at=job_data["updated_at"],
    )


@router.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """
    List all analysis jobs for the current user.
    """
    if not user:
        user = get_or_create_default_user(db)

    documents = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    # For each document, get job status from in-memory or from document itself
    result = []
    for doc in documents:
        job_id = str(doc.id)  # using document id as job id for simplicity
        job_data = processing_jobs.get(job_id)
        if job_data:
            result.append(
                JobStatusResponse(
                    job_id=job_id,
                    status=job_data["status"],
                    result=job_data["result"],
                    error_message=job_data.get("error"),
                    updated_at=job_data["updated_at"],
                )
            )
        else:
            result.append(
                JobStatusResponse(
                    job_id=job_id,
                    status=doc.status,
                    result=None,
                    error_message=None,
                    updated_at=doc.updated_at,
                )
            )
    return result


async def process_document_async(
    document_id: uuid.UUID,
    job_id: uuid.UUID,
    file: UploadFile,
    jurisdiction: str,
    project_id: Optional[str],
    db_session: Session,
):
    """
    Background task that runs the multi-agent pipeline on the uploaded document.

    This function orchestrates:
    1. PlanInspector - extracts structural and textual content
    2. JurisdictionOrchestrator - determines applicable codes
    3. CodeMatcher - matches violations against code references
    4. ReportGenerator - produces the forensic evidence dossier
    5. WormLedger - logs immutable audit trail
    """
    # Use a new session for this background task (the passed session might be from request)
    db = next(get_db())
    try:
        logger.info("Starting background processing for job %s", job_id)

        # Update in-memory status
        processing_jobs[str(job_id)] = {
            "status": "processing",
            "result": None,
            "error": None,
            "updated_at": datetime.utcnow(),
        }

        # Update document status in DB
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "processing"
            db.commit()

        # Step 1: PlanInspector - analyze document structure and content
        inspector = PlanInspector()
        doc_content = await inspector.analyze(file)

        # Step 2: JurisdictionOrchestrator - fetch relevant code books
        orchestrator = JurisdictionOrchestrator()
        codes = await orchestrator.get_codes(jurisdiction)

        # Step 3: CodeMatcher - identify violations
        matcher = CodeMatcher()
        violations = await matcher.match(doc_content, codes)

        # Step 4: ReportGenerator - compile forensic facts dossier
        generator = ReportGenerator()
        report = await generator.generate_report(
            document_id=document_id,
            violations=violations,
            jurisdiction=jurisdiction,
        )

        # Step 5: WormLedger - append immutable audit record
        ledger = WormLedger()
        await ledger.record_analysis(
            document_id=document_id,
            job_id=job_id,
            report=report,
        )

        # Update in-memory with success
        processing_jobs[str(job_id)] = {
            "status": "completed",
            "result": report,
            "error": None,
            "updated_at": datetime.utcnow(),
        }

        # Update document status and store results (optionally link report)
        if document:
            document.status = "completed"
            document.updated_at = datetime.utcnow()
            db.commit()

        logger.info("Background processing completed for job %s", job_id)

    except Exception as e:
        logger.exception("Background processing failed for job %s", job_id)
        # Update in-memory with error
        processing_jobs[str(job_id)] = {
            "status": "failed",
            "result": None,
            "error": str(e),
            "updated_at": datetime.utcnow(),
        }
        # Update document status in DB
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "failed"
            document.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
