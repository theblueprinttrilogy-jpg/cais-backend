"""
CAIS Code Compliance - Upload Endpoint Module

Handles document upload, multi-agent pipeline orchestration,
and background processing for code compliance analysis.

The multi-agent system consists of:
- PlanInspector: Extracts structural and textual content from documents
- JurisdictionOrchestrator: Determines applicable building codes
- CodeMatcher: Identifies code violations
- ReportGenerator: Produces forensic evidence dossiers
- WormLedger: Logs immutable audit trail entries
"""

import uuid
import logging
import os
import shutil
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import User, Document, Project, Violation, Report, WORMLedgerEntry
from app.agents.plan_inspector import PlanInspector
from app.agents.jurisdiction_orchestrator import JurisdictionOrchestrator
from app.agents.code_matcher import CodeMatcher
from app.agents.report_generator import ReportGenerator
from app.agents.worm_ledger import WormLedger
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


def get_or_create_project(
    db: Session,
    user: User,
    project_identifier: Optional[str]
) -> Optional[Project]:
    """
    Retrieve an existing project by ID or name, or create a new one.

    If project_identifier is a valid UUID, try to find the project by ID.
    If not found or if it's a string name, look up by name (case-sensitive).
    If no project exists, create a new one with the given name.

    Args:
        db: Database session.
        user: The user who owns the project.
        project_identifier: Either a UUID string or a project name.

    Returns:
        The Project instance, or None if no identifier was provided.
    """
    if not project_identifier:
        return None

    # Attempt to parse as UUID (existing project ID)
    try:
        project_uuid = uuid.UUID(project_identifier)
        project = db.query(Project).filter(Project.id == project_uuid).first()
        if project:
            logger.info("Found existing project by UUID: %s", project_uuid)
            return project
    except ValueError:
        pass  # Not a UUID, treat as name

    # Look up by name
    project = db.query(Project).filter(Project.name == project_identifier).first()
    if project:
        logger.info("Found existing project by name: %s", project_identifier)
        return project

    # Create a new project with the provided name (generate new UUID)
    new_project = Project(
        id=uuid.uuid4(),
        name=project_identifier,
        user_id=user.id,
        created_at=datetime.utcnow(),
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    logger.info("Created new project: %s (ID: %s)", project_identifier, new_project.id)
    return new_project


@router.post("/file", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    jurisdiction: str = Form(...),
    project_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a document for code compliance analysis.

    - **file**: The document to analyze (PDF, image, etc.)
    - **jurisdiction**: Legal jurisdiction for code references (e.g., "NYC", "CA")
    - **project_id**: Optional project identifier (UUID or project name)
    """
    # Use default user (no authentication required)
    user = get_or_create_default_user(db)

    # Validate file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Resolve or create project
    project = get_or_create_project(db, user, project_id)

    # Generate unique identifiers
    document_id = uuid.uuid4()
    job_id = uuid.uuid4()

    # Create storage directory if it doesn't exist
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)

    # Save file to temporary storage
    file_extension = os.path.splitext(file.filename)[1] or ".bin"
    temp_filename = f"{uuid.uuid4()}{file_extension}"
    temp_path = os.path.join(settings.STORAGE_PATH, temp_filename)

    # Write file content to disk
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error("Failed to save uploaded file: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Create document record using only valid columns of the Document model.
    # Valid attributes: id, filename, file_path, project_id, status.
    # Timestamps like created_at/updated_at are automatically handled by the database.
    document = Document(
        id=document_id,
        filename=file.filename,
        file_path=temp_path,
        project_id=project.id if project else None,
        status="queued",
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
        file_path=temp_path,
        jurisdiction=jurisdiction,
        project_id=project_id,      # pass original identifier (if needed)
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
):
    """
    Retrieve the status of an analysis job.

    - **job_id**: UUID of the analysis job (matches document ID)
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
        # Use document.updated_at if it exists, else fallback to current time
        updated_at = getattr(document, "updated_at", datetime.utcnow())
        return JobStatusResponse(
            job_id=job_id,
            status=document.status,
            result=None,
            error_message=None,
            updated_at=updated_at,
        )

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
):
    """
    List all analysis jobs (since no user association on Document).
    """
    # Since Document does not have a user_id column, we return all documents.
    documents = (
        db.query(Document)
        .order_by(Document.created_at.desc() if hasattr(Document, "created_at") else Document.id.desc())
        .all()
    )

    result = []
    for doc in documents:
        # Use document id as job id
        job_id = str(doc.id)
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
            updated_at = getattr(doc, "updated_at", datetime.utcnow())
            result.append(
                JobStatusResponse(
                    job_id=job_id,
                    status=doc.status,
                    result=None,
                    error_message=None,
                    updated_at=updated_at,
                )
            )
    return result


async def process_document_async(
    document_id: uuid.UUID,
    job_id: uuid.UUID,
    file_path: str,
    jurisdiction: str,
    project_id: Optional[str],
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
    # Create a new database session for this background task
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
            # If the model has an updated_at column, set it
            if hasattr(document, "updated_at"):
                document.updated_at = datetime.utcnow()
            db.commit()

        # Step 1: PlanInspector - analyze document structure and content
        inspector = PlanInspector()
        doc_content = await inspector.analyze_file(file_path)

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

        # Update document status and store results
        if document:
            document.status = "completed"
            if hasattr(document, "updated_at"):
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
            if hasattr(document, "updated_at"):
                document.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
