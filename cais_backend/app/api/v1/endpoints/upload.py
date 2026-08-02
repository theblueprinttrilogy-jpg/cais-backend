"""
Upload and Processing Endpoint - CAIS Code Compliance

This module handles PDF upload, triggers the multi-agent analysis pipeline,
and tracks job status. It uses:
- PlanInspector: Visual scanning at 200 DPI
- JurisdictionOrchestrator: Address detection and jurisdiction mapping
- CodeMatcher: Semantic search in pgvector with yellow highlighting
- ReportGenerator: Forensic Facts Dossier generation
- WormLedger: Immutable evidence recording

Based on CAIS CODE COMPLIANCE WORKFLOW - Chapter 3 and 4
"""

import os
import uuid
import shutil
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from app.agents.plan_inspector import PlanInspector
from app.agents.jurisdiction_orchestrator import JurisdictionOrchestrator
from app.agents.code_matcher import CodeMatcher
from app.agents.report_generator import ReportGenerator
from app.agents.worm_ledger import WormLedger
from app.core.database import SessionLocal
from app.db.models import Document, Project, Violation, Report, WORMLedgerEntry, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

# Upload directory
UPLOAD_DIR = Path("/tmp/cais_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Processing jobs tracking
processing_jobs: Dict[str, Dict[str, Any]] = {}


# ============================================================
# HELPER: Get or create default user
# ============================================================

def get_or_create_default_user(db) -> User:
    """
    Get or create a default system user for unauthenticated uploads.
    """
    default_user_id = "00000000-0000-0000-0000-000000000000"
    user = db.query(User).filter(User.id == default_user_id).first()
    if not user:
        user = User(
            id=default_user_id,
            email="system@cais.local",
            username="system",
            hashed_password="",  # No password needed for system
            full_name="System User",
            is_active=True,
            is_superuser=True,
            is_verified=True,
            subscription_plan="free",
            preferred_language="en",
            preferred_timezone="UTC"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created default system user with ID: {user.id}")
    return user


# ============================================================
# HELPER: Get or create project from project_id (string)
# ============================================================

def get_or_create_project(db, user: User, project_id: str) -> Project:
    """
    Get existing project if project_id is a valid UUID, otherwise create a new one.
    """
    project = None
    # Try to parse as UUID
    try:
        project_uuid = uuid.UUID(project_id)
        project = db.query(Project).filter(Project.id == project_uuid).first()
    except ValueError:
        # Not a valid UUID, treat as project name
        pass

    if not project:
        # Create new project with generated UUID and use project_id as name
        new_uuid = uuid.uuid4()
        project = Project(
            id=new_uuid,
            user_id=user.id,
            name=project_id,
            status="active"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created new project with ID: {project.id}, name: {project_id}")
    else:
        logger.info(f"Found existing project with ID: {project.id}")

    return project


# ============================================================
# BACKGROUND PROCESSING
# ============================================================

async def process_document_async(job_id: str, file_path: Path, filename: str, project_uuid: str):
    """
    Process document using the full CAIS multi-agent pipeline.
    """
    db = SessionLocal()
    try:
        # Update job status
        processing_jobs[job_id]["status"] = "processing"
        processing_jobs[job_id]["steps"]["upload"]["status"] = "done"

        # Step 1: PlanInspector - Convert PDF to images at 200 DPI and scan
        logger.info(f"[{job_id}] Phase 1: PlanInspector - Visual scanning")
        processing_jobs[job_id]["steps"]["plan_inspector"]["status"] = "processing"

        plan_inspector = PlanInspector()
        document = db.query(Document).filter(Document.task_id == job_id).first()
        if not document:
            raise ValueError(f"Document not found for task_id: {job_id}")

        scan_result = plan_inspector.analyze(document)
        processing_jobs[job_id]["steps"]["plan_inspector"]["status"] = "done"
        processing_jobs[job_id]["steps"]["plan_inspector"]["timestamp"] = datetime.now().isoformat()

        # Extract address from scan result
        address = scan_result.get('address')
        jurisdiction_code = scan_result.get('jurisdiction')

        # Step 2: JurisdictionOrchestrator - Identify jurisdiction
        logger.info(f"[{job_id}] Phase 2: JurisdictionOrchestrator")
        processing_jobs[job_id]["steps"]["jurisdiction"]["status"] = "processing"

        juris_orchestrator = JurisdictionOrchestrator(db)
        if address:
            jurisdiction_info = juris_orchestrator.identify_jurisdiction(address)
            jurisdiction_code = jurisdiction_info.get('jurisdiction', 'Unknown')
            # Update project with jurisdiction
            project = db.query(Project).filter(Project.id == project_uuid).first()
            if project:
                project.jurisdiction = jurisdiction_code
                project.address = address
                db.commit()
        else:
            jurisdiction_info = {'jurisdiction': 'Unknown', 'state': 'Unknown', 'code_set': 'IBC', 'confidence': 0.0}

        processing_jobs[job_id]["steps"]["jurisdiction"]["status"] = "done"
        processing_jobs[job_id]["steps"]["jurisdiction"]["timestamp"] = datetime.now().isoformat()
        processing_jobs[job_id]["results"]["address"] = address
        processing_jobs[job_id]["results"]["jurisdiction"] = jurisdiction_info

        # Step 3: CodeMatcher - Search for violations in pgvector
        logger.info(f"[{job_id}] Phase 3: CodeMatcher - Semantic search")
        processing_jobs[job_id]["steps"]["code_matcher"]["status"] = "processing"

        code_matcher = CodeMatcher(db)
        matched_violations = []
        for violation_data in scan_result.get('violations', []):
            # Create Violation record in DB
            violation = Violation(
                document_id=document.id,
                violation_type=violation_data.get('type', 'unknown'),
                severity=violation_data.get('severity', 'warning'),
                description=violation_data.get('description', ''),
                code_reference=violation_data.get('code_reference', ''),
                coordinates=violation_data.get('coordinates'),
                evidence_path=violation_data.get('evidence_path'),
                page_num=violation_data.get('page_num'),
                status='detected'
            )
            db.add(violation)
            db.commit()
            db.refresh(violation)

            # Match against codes
            matches = code_matcher.analyze(violation, jurisdiction_code)
            for match in matches:
                matched_violations.append({
                    'violation_id': str(violation.id),
                    'code_type': match.get('code_type'),
                    'section': match.get('section'),
                    'title': match.get('title'),
                    'description': match.get('description'),
                    'similarity': match.get('similarity', 0),
                    'highlighted': match.get('highlighted', ''),
                    'jurisdiction': jurisdiction_code
                })

        processing_jobs[job_id]["steps"]["code_matcher"]["status"] = "done"
        processing_jobs[job_id]["steps"]["code_matcher"]["timestamp"] = datetime.now().isoformat()
        processing_jobs[job_id]["results"]["violations"] = matched_violations

        # Step 4: ReportGenerator - Create Forensic Facts Dossier
        logger.info(f"[{job_id}] Phase 4: ReportGenerator - Creating dossier")
        processing_jobs[job_id]["steps"]["report_generator"]["status"] = "processing"

        report_generator = ReportGenerator()
        # Prepare violations with evidence for the report
        violations_for_report = []
        for v in db.query(Violation).filter(Violation.document_id == document.id).all():
            violations_for_report.append({
                'id': str(v.id),
                'type': v.violation_type,
                'severity': v.severity,
                'description': v.description,
                'code_reference': v.code_reference,
                'evidence_path': v.evidence_path,
                'page_num': v.page_num,
                'code_evidence_paths': []  # Will be populated if we have code screenshots
            })

        dossier_path = report_generator.generate_dossier(
            violations_for_report,
            document.language or 'en'
        )

        # Create Report record in DB
        report = Report(
            document_id=document.id,
            file_path=dossier_path,
            language=document.language or 'en',
            download_count=0
        )
        db.add(report)
        db.commit()

        processing_jobs[job_id]["steps"]["report_generator"]["status"] = "done"
        processing_jobs[job_id]["steps"]["report_generator"]["timestamp"] = datetime.now().isoformat()
        processing_jobs[job_id]["results"]["report_path"] = dossier_path

        # Step 5: WormLedger - Immutable record
        logger.info(f"[{job_id}] Phase 5: WormLedger - Immutable recording")
        processing_jobs[job_id]["steps"]["worm_ledger"]["status"] = "processing"

        worm_ledger = WormLedger(db)
        for v in db.query(Violation).filter(Violation.document_id == document.id).all():
            worm_ledger.record_violation(
                document_id=str(document.id),
                violation_id=str(v.id),
                violation_data={
                    'type': v.violation_type,
                    'severity': v.severity,
                    'description': v.description,
                    'code_reference': v.code_reference,
                    'evidence_path': v.evidence_path,
                    'page_num': v.page_num
                },
                jurisdiction=jurisdiction_code
            )

        processing_jobs[job_id]["steps"]["worm_ledger"]["status"] = "done"
        processing_jobs[job_id]["steps"]["worm_ledger"]["timestamp"] = datetime.now().isoformat()

        # Mark document as completed
        document.status = "completed"
        db.commit()

        # Mark job as completed
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["completed_at"] = datetime.now().isoformat()

        logger.info(f"[{job_id}] Processing completed successfully")

    except Exception as e:
        logger.error(f"[{job_id}] Processing error: {e}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["error"] = str(e)
        # Update document status
        try:
            doc = db.query(Document).filter(Document.task_id == job_id).first()
            if doc:
                doc.status = "failed"
                db.commit()
        except:
            pass
    finally:
        db.close()


# ============================================================
# API ENDPOINTS
# ============================================================

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = "default"
) -> Dict[str, Any]:
    """
    Upload a PDF file and start the CAIS multi-agent analysis pipeline.

    Only PDF files are accepted.
    """
    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted"
        )

    # Validate file size (max 50MB)
    file_size = 0
    temp_file = UPLOAD_DIR / f"temp_{uuid.uuid4().hex[:8]}.pdf"
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        file_size = temp_file.stat().st_size

    if file_size > 50 * 1024 * 1024:
        temp_file.unlink()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{job_id}_{file.filename}"
    final_path = UPLOAD_DIR / safe_filename
    temp_file.rename(final_path)

    logger.info(f"File uploaded: {safe_filename} (Job ID: {job_id})")

    # Initialize job status
    processing_jobs[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "filepath": str(final_path),
        "status": "uploaded",
        "project_id": project_id,  # store original for reference
        "steps": {
            "upload": {"status": "done", "timestamp": datetime.now().isoformat()},
            "plan_inspector": {"status": "pending", "timestamp": None},
            "jurisdiction": {"status": "pending", "timestamp": None},
            "code_matcher": {"status": "pending", "timestamp": None},
            "report_generator": {"status": "pending", "timestamp": None},
            "worm_ledger": {"status": "pending", "timestamp": None}
        },
        "results": {},
        "created_at": datetime.now().isoformat()
    }

    # Create Document record in DB
    db = SessionLocal()
    try:
        # Get or create default user
        user = get_or_create_default_user(db)

        # Get or create project
        project = get_or_create_project(db, user, project_id)

        # Store project UUID for background task
        project_uuid = str(project.id)

        document = Document(
            task_id=job_id,
            project_id=project.id,
            filename=file.filename,
            file_path=str(final_path),
            file_size=file_size,
            file_type="application/pdf",
            language="en",
            status="uploaded"
        )
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception as e:
        logger.error(f"Error creating document record: {e}")
        db.rollback()
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["error"] = f"Database error: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    finally:
        db.close()

    # Start background processing with project_uuid
    asyncio.create_task(process_document_async(job_id, final_path, file.filename, project_uuid))

    return {
        "status": "success",
        "message": "File uploaded successfully. Processing started.",
        "data": {
            "job_id": job_id,
            "filename": file.filename,
            "status": "processing"
        }
    }


@router.get("/status/{job_id}")
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """Get the processing status of a job."""
    if job_id not in processing_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job = processing_jobs[job_id]
    return {
        "status": "success",
        "data": {
            "job_id": job["id"],
            "filename": job["filename"],
            "overall_status": job["status"],
            "steps": job["steps"],
            "results": job.get("results", {}),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "error": job.get("error")
        }
    }


@router.get("/jobs")
async def list_jobs() -> Dict[str, Any]:
    """List all processing jobs."""
    jobs = []
    for job_id, job in processing_jobs.items():
        jobs.append({
            "job_id": job_id,
            "filename": job["filename"],
            "status": job["status"],
            "created_at": job.get("created_at")
        })
    return {"status": "success", "data": {"total": len(jobs), "jobs": jobs}}


@router.delete("/job/{job_id}")
async def delete_job(job_id: str) -> Dict[str, Any]:
    """Delete a processing job and its associated files."""
    if job_id not in processing_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job = processing_jobs[job_id]
    filepath = job.get("filepath")
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass

    del processing_jobs[job_id]
    return {"status": "success", "message": f"Job {job_id} deleted"}
