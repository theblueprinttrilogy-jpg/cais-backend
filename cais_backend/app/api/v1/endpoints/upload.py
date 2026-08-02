"""
CAIS Code Compliance - Upload Endpoint Module

Handles document upload, multi-agent pipeline orchestration,
and background processing for code compliance analysis.
"""

import uuid
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import User, Document, AnalysisJob, WormLedger
from app.core.security import get_current_user
from app.services.pipeline import (
    PlanInspector,
    JurisdictionOrchestrator,
    CodeMatcher,
    ReportGenerator,
    WormLedger as WormLedgerService,
)
from app.schemas.upload import UploadResponse, JobStatusResponse
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


def get_or_create_default_user(db: Session) -> User:
    """
    Get or create a default user for anonymous uploads.

    Returns:
        User: The default user instance.
    """
    # Use a fixed UUID for the default user
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for code compliance analysis.

    - **file**: The document to analyze (PDF, image, etc.)
    - **jurisdiction**: Legal jurisdiction for code references (e.g., "NYC", "CA")
    - **project_id**: Optional project ID to associate the document
    """
    # If no user is authenticated, use default user
    if not user:
        user = get_or_create_default_user(db)

    # Validate file type and size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Save file to temporary storage
    file_path = f"{settings.STORAGE_PATH}/{uuid.uuid4()}_{file.filename}"
    # In production, use cloud storage; here we simulate
    # For now, we just store metadata; actual file saving is delegated to pipeline

    # Create document record
    document = Document(
        id=uuid.uuid4(),
        filename=file.filename,
        file_path=file_path,
        jurisdiction=jurisdiction,
        project_id=project_id,
        user_id=user.id,
        status="pending",
        uploaded_at=datetime.utcnow(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Create analysis job
    job = AnalysisJob(
        id=uuid.uuid4(),
        document_id=document.id,
        status="queued",
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    # Schedule background processing
    background_tasks.add_task(
        process_document_async,
        document_id=document.id,
        job_id=job.id,
        file=file,
        jurisdiction=jurisdiction,
        project_id=project_id,
    )

    return UploadResponse(
        job_id=str(job.id),
        document_id=str(document.id),
        status="queued",
        message="Document uploaded and queued for analysis.",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retrieve the status of an analysis job.

    - **job_id**: UUID of the analysis job
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ensure user has access (if authenticated)
    if user and job.document.user_id != user.id:
        # Admin or shared access could be extended
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        result=job.result,
        error_message=job.error_message,
        updated_at=job.updated_at,
    )


@router.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List all analysis jobs for the current user.
    """
    if not user:
        # For anonymous, return recent default user jobs
        user = get_or_create_default_user(db)

    jobs = (
        db.query(AnalysisJob)
        .join(Document)
        .filter(Document.user_id == user.id)
        .order_by(AnalysisJob.created_at.desc())
        .all()
    )

    return [
        JobStatusResponse(
            job_id=str(job.id),
            status=job.status,
            result=job.result,
            error_message=job.error_message,
            updated_at=job.updated_at,
        )
        for job in jobs
    ]


async def process_document_async(
    document_id: uuid.UUID,
    job_id: uuid.UUID,
    file: UploadFile,
    jurisdiction: str,
    project_id: Optional[str] = None,
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
    db = next(get_db())  # Manual session for background task
    try:
        logger.info("Starting background processing for job %s", job_id)

        # Update job status to processing
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if job:
            job.status = "processing"
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
        ledger = WormLedgerService()
        await ledger.record_analysis(
            document_id=document_id,
            job_id=job_id,
            report=report,
        )

        # Update job with success
        if job:
            job.status = "completed"
            job.result = report
            job.updated_at = datetime.utcnow()
            db.commit()

        logger.info("Background processing completed for job %s", job_id)

    except Exception as e:
        logger.exception("Background processing failed for job %s", job_id)
        # Update job with error
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
