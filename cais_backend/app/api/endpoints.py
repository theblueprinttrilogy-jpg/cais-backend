"""
app/api/endpoints.py

FastAPI endpoints for CAIS Code Compliance backend.
Provides semantic search, deterministic compliance audit,
multi-format file upload, job status polling, and dashboard data endpoints.
All using SQLAlchemy 2.0 async patterns with real database queries.

KPI calculations for /api/dashboard/stats are based on *actual detected violations*
extracted from completed AgentTask results, not on the general CodeReference table.
If no violations exist, metrics default to clean state:
- Value at Risk = 0
- Active Liens = 0
- Compliance % = 100.0
- Risk Score = 1.0

IMPORTANT: The SQLAlchemy model `File` is imported as `FileModel` to
avoid name collision with FastAPI's `File` dependency utility.
"""

import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sentence_transformers import SentenceTransformer

# Import required models and session factory
from app.models.code_reference import CodeReference
from app.models.agent import Agent, AgentTask
from app.models.file import File as FileModel
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Initialize the embedding model
MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(MODEL_NAME)

# Allowed file extensions for construction, CAD, BIM formats
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt",
    ".png", ".jpg", ".jpeg",
    ".dwg", ".dxf",
    ".xls", ".xlsx"
}

# Severity cost model for Value at Risk (per violation)
SEVERITY_COST = {
    "critical": 12500,
    "high": 6000,
    "medium": 2500,
    "low": 1000,
    # Default for unknown severity
    "default": 1000,
}

# Penalty percentages for Compliance (per violation)
SEVERITY_PENALTY = {
    "critical": 15.0,
    "high": 8.0,
    "medium": 4.0,
    "low": 1.0,
    # Default for unknown severity
    "default": 1.0,
}

# Risk weights for Risk Score (per violation)
SEVERITY_WEIGHT = {
    "critical": 10,
    "high": 5,
    "medium": 2,
    "low": 1,
    # Default
    "default": 1,
}


# -------------------- Pydantic Models --------------------

class SearchRequest(BaseModel):
    """Request model for semantic vector search."""
    query: str = Field(..., description="Natural language query to search code references.")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return.")


class SearchResultItem(BaseModel):
    """Single search result item with similarity score."""
    id: int
    section: str
    title: Optional[str]
    description: Optional[str]
    full_text: Optional[str]
    jurisdiction: str
    code_type: str
    severity: Optional[str]
    similarity: float


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str
    results: List[SearchResultItem]


class AuditRequest(BaseModel):
    """Request model for compliance audit."""
    jurisdiction: str = Field(..., description="Jurisdiction (e.g., 'US-FL')")
    code_type: str = Field(..., description="Type of code (e.g., 'building', 'fire')")
    compliant_sections: List[str] = Field(
        default_factory=list,
        description="List of section identifiers that the building already complies with."
    )


class ViolationItem(BaseModel):
    """Single violation record."""
    section: str
    title: Optional[str]
    description: Optional[str]
    severity: Optional[str]
    required: bool = True


class AuditResponse(BaseModel):
    """Response model for audit endpoint."""
    jurisdiction: str
    code_type: str
    total_required_sections: int
    compliant_sections_count: int
    violations: List[ViolationItem]
    total_violations: int
    status: str


class UploadFileResponse(BaseModel):
    """Response model for file upload."""
    status: str
    job_id: str
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response model for job status polling."""
    status: str
    data: Dict[str, Any]


class DashboardStatsResponse(BaseModel):
    """Response model for dashboard KPI stats."""
    status: str
    data: Dict[str, Any]


class DashboardHistoryResponse(BaseModel):
    """Response model for dashboard history."""
    status: str
    data: List[Dict[str, Any]]


class DashboardProjectResponse(BaseModel):
    """Response model for dashboard project info."""
    status: str
    data: Dict[str, Any]


class DashboardCodesResponse(BaseModel):
    """Response model for dashboard codes list."""
    status: str
    data: List[Dict[str, Any]]


class VerifyAddressRequest(BaseModel):
    address: str


class VerifyAddressResponse(BaseModel):
    status: str
    data: Dict[str, Any]


# -------------------- Dependency --------------------

async def get_db() -> AsyncSession:
    """Provide an asynchronous database session."""
    async with async_session_factory() as session:
        yield session


# -------------------- Helper Functions --------------------

def get_file_extension(filename: str) -> str:
    """Return lowercase file extension including dot."""
    return os.path.splitext(filename)[1].lower()


def is_allowed_extension(filename: str) -> bool:
    """Check if file extension is in allowed list."""
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Save an uploaded file to a given destination path (synchronous I/O)."""
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


async def _get_or_create_agent(db: AsyncSession, agent_name: str) -> Agent:
    """
    Retrieve an Agent by name from the database, or create one if missing.

    :param db: Async SQLAlchemy session.
    :param agent_name: Name of the agent.
    :return: Agent instance.
    """
    stmt = select(Agent).where(Agent.name == agent_name)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        logger.info(f"Agent '{agent_name}' not found in DB, creating...")
        agent = Agent(
            name=agent_name,
            description=f"Auto-created agent for '{agent_name}'",
            is_active=1,
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        logger.info(f"Agent '{agent_name}' created with ID {agent.id}")

    return agent


def _extract_violation_severities_from_task(task: AgentTask) -> List[str]:
    """
    Extract violation severities from a completed AgentTask's result field.
    Returns a list of severity strings (e.g., ['critical', 'high', ...]).
    If no violations found, returns empty list.
    """
    if not task.result or task.status != "completed":
        return []

    result = task.result
    if not isinstance(result, dict):
        return []

    # Try multiple possible structures
    violations = []
    if "violations" in result and isinstance(result["violations"], list):
        # Each violation might be a dict with 'severity' key
        for v in result["violations"]:
            if isinstance(v, dict) and "severity" in v:
                severity = v["severity"]
                if severity:
                    violations.append(severity.lower())
            elif isinstance(v, str):
                # If violation is a string, use default severity
                violations.append("default")
    elif "violation_count" in result and "severity" in result:
        # If result has direct severity count
        sev = result.get("severity", "default")
        count = result.get("violation_count", 0)
        violations.extend([sev.lower()] * count)
    elif "detected_violations" in result and isinstance(result["detected_violations"], list):
        for v in result["detected_violations"]:
            if isinstance(v, dict) and "severity" in v:
                violations.append(v["severity"].lower())
            else:
                violations.append("default")
    else:
        # Fallback: if any result exists but no structured violations, treat as default
        violations = ["default"]  # placeholder to show something

    return violations


# ================================================================
# ROUTER 1: API v1 (Search & Audit)
# ================================================================
router_v1 = APIRouter(prefix="/api/v1", tags=["code-compliance"])


@router_v1.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
) -> SearchResponse:
    """
    Perform semantic vector similarity search over code references.
    """
    logger.info(f"Semantic search query: '{request.query}'")

    query_embedding = embedding_model.encode(request.query, normalize_embeddings=True).tolist()

    stmt = select(
        CodeReference,
        (1 - CodeReference.embedding.cosine_distance(query_embedding)).label("similarity")
    ).order_by(
        CodeReference.embedding.cosine_distance(query_embedding)
    ).limit(request.limit)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for ref, similarity in rows:
        items.append(SearchResultItem(
            id=ref.id,
            section=ref.section,
            title=ref.title,
            description=ref.description,
            full_text=ref.full_text,
            jurisdiction=ref.jurisdiction,
            code_type=ref.code_type,
            severity=ref.severity,
            similarity=similarity
        ))

    logger.info(f"Search returned {len(items)} results.")
    return SearchResponse(query=request.query, results=items)


@router_v1.post("/audit", response_model=AuditResponse)
async def compliance_audit(
    request: AuditRequest,
    db: AsyncSession = Depends(get_db)
) -> AuditResponse:
    """
    Perform a deterministic compliance audit.
    """
    logger.info(
        f"Audit request: jurisdiction={request.jurisdiction}, "
        f"code_type={request.code_type}, compliant_sections={request.compliant_sections}"
    )

    stmt = select(CodeReference).where(
        CodeReference.jurisdiction == request.jurisdiction,
        CodeReference.code_type == request.code_type
    )
    result = await db.execute(stmt)
    required_refs = result.scalars().all()

    if not required_refs:
        logger.warning(f"No regulations found for {request.jurisdiction}/{request.code_type}")
        return AuditResponse(
            jurisdiction=request.jurisdiction,
            code_type=request.code_type,
            total_required_sections=0,
            compliant_sections_count=len(request.compliant_sections),
            violations=[],
            total_violations=0,
            status="compliant"
        )

    compliant_set = set(request.compliant_sections)
    violations = []
    for ref in required_refs:
        if ref.section not in compliant_set:
            violations.append(ViolationItem(
                section=ref.section,
                title=ref.title,
                description=ref.description,
                severity=ref.severity
            ))

    total_required = len(required_refs)
    compliant_count = total_required - len(violations)
    status_val = "compliant" if len(violations) == 0 else "non-compliant"

    logger.info(f"Audit complete: {len(violations)} violations found.")
    return AuditResponse(
        jurisdiction=request.jurisdiction,
        code_type=request.code_type,
        total_required_sections=total_required,
        compliant_sections_count=compliant_count,
        violations=violations,
        total_violations=len(violations),
        status=status_val
    )


# ================================================================
# ROUTER 2: Dashboard API
# ================================================================
router_dashboard = APIRouter(prefix="/api", tags=["dashboard"])


@router_dashboard.post("/upload/file", response_model=UploadFileResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(..., description="Construction document (PDF, DOCX, TXT, PNG, JPG, DWG, DXF, XLS, XLSX)"),
    db: AsyncSession = Depends(get_db)
) -> UploadFileResponse:
    """
    Upload a construction document in any supported format.
    """
    logger.info(f"Received upload: filename={file.filename}")

    if not is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    task_id = str(uuid.uuid4())
    ext = get_file_extension(file.filename)
    temp_dir = "/tmp/cais_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{task_id}{ext}")

    try:
        save_upload_file(file, temp_file_path)
        logger.info(f"File saved to {temp_file_path}")

        agent = await _get_or_create_agent(db, "ingestion")

        task = AgentTask(
            id=task_id,
            agent_id=agent.id,
            agent_name="ingestion",
            status="processing",
            priority=5,
            input_data={
                "file_path": temp_file_path,
                "original_filename": file.filename,
                "uploaded_at": datetime.utcnow().isoformat()
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        logger.info(f"Task {task_id} created for file {file.filename}")

        return UploadFileResponse(
            status="success",
            job_id=task_id,
            message="File accepted. Processing will begin shortly."
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload."
        )


@router_dashboard.get("/upload/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> JobStatusResponse:
    """
    Poll the status of an asynchronous job.
    """
    stmt = select(AgentTask).where(AgentTask.id == job_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    steps = {}
    if task.status == "pending":
        steps["upload"] = {"status": "pending"}
        steps["process"] = {"status": "pending"}
    elif task.status == "processing":
        steps["upload"] = {"status": "done"}
        steps["process"] = {"status": "processing"}
    elif task.status == "completed":
        steps["upload"] = {"status": "done"}
        steps["process"] = {"status": "done"}
    elif task.status == "failed":
        steps["upload"] = {"status": "done"}
        steps["process"] = {"status": "failed"}
    else:
        steps["upload"] = {"status": "unknown"}
        steps["process"] = {"status": "unknown"}

    overall_status = task.status
    if overall_status == "pending":
        overall_status = "uploaded"

    response_data = {
        "overall_status": overall_status,
        "steps": steps,
    }

    if task.status == "completed" and task.result:
        response_data["results"] = task.result
    elif task.status == "failed":
        response_data["error"] = task.error or "Processing error occurred."

    return JobStatusResponse(status="success", data=response_data)


@router_dashboard.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
) -> DashboardStatsResponse:
    """
    Return KPI metrics for the dashboard computed from actual detected violations
    extracted from completed AgentTask results.

    If no violations are found, metrics default to:
    - Value at Risk: 0
    - Active Liens: 0
    - Compliance %: 100.0
    - Risk Score: 1.0
    """
    # Query all completed tasks with result not None
    stmt = select(AgentTask).where(
        AgentTask.status == "completed",
        AgentTask.result.is_not(None)
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    # Aggregate violation severities from all tasks
    severity_counts = {}
    for task in tasks:
        severities = _extract_violation_severities_from_task(task)
        for sev in severities:
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

    total_violations = sum(severity_counts.values())

    # Default clean state if no violations
    if total_violations == 0:
        stats = {
            "value_at_risk": 0,
            "active_liens": 0,
            "compliance_percent": 100.0,
            "risk_score": 1.0
        }
        return DashboardStatsResponse(status="success", data=stats)

    # --- Value at Risk ---
    var_total = 0
    for sev, cnt in severity_counts.items():
        cost = SEVERITY_COST.get(sev, SEVERITY_COST["default"])
        var_total += cnt * cost

    # --- Active Liens ---
    # No liens table exists; return 0 as per requirement
    active_liens = 0

    # --- Compliance Percentage ---
    # Start at 100%, subtract penalty per violation based on severity
    compliance_percent = 100.0
    for sev, cnt in severity_counts.items():
        penalty = SEVERITY_PENALTY.get(sev, SEVERITY_PENALTY["default"])
        compliance_percent -= cnt * penalty

    # Ensure it doesn't go below 0
    compliance_percent = max(0.0, compliance_percent)
    compliance_percent = round(compliance_percent, 1)

    # --- Risk Score ---
    # Weighted sum using severity weights, normalize to 0-100
    weighted_sum = 0
    for sev, cnt in severity_counts.items():
        weight = SEVERITY_WEIGHT.get(sev, SEVERITY_WEIGHT["default"])
        weighted_sum += cnt * weight

    # Maximum possible if all violations were critical (weight 10)
    max_weighted = total_violations * max(SEVERITY_WEIGHT.values())
    risk_score = round((weighted_sum / max_weighted) * 100, 1) if max_weighted > 0 else 0.0
    # Clamp to 1-100
    risk_score = max(1.0, min(100.0, risk_score))

    stats = {
        "value_at_risk": var_total,
        "active_liens": active_liens,
        "compliance_percent": compliance_percent,
        "risk_score": risk_score
    }
    return DashboardStatsResponse(status="success", data=stats)


@router_dashboard.get("/dashboard/history", response_model=DashboardHistoryResponse)
async def get_dashboard_history(
    db: AsyncSession = Depends(get_db)
) -> DashboardHistoryResponse:
    """
    Return a list of recent output history entries from the AgentTask table.
    If no tasks exist, returns an empty array.
    """
    try:
        stmt = select(AgentTask).order_by(desc(AgentTask.created_at)).limit(20)
        result = await db.execute(stmt)
        tasks = result.scalars().all()
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        # Return empty array gracefully
        return DashboardHistoryResponse(status="success", data=[])

    history_entries = []
    for task in tasks:
        # Safely build message - convert UUID to string before slicing
        task_id_short = str(task.id)[:8] if task.id else "Task"
        message = f"Task {task_id_short}"
        if task.agent_name:
            message += f" ({task.agent_name})"
        if task.status == "completed":
            message += " completed successfully"
        elif task.status == "failed":
            message += f" failed: {task.error or 'unknown error'}"
        elif task.status == "processing":
            message += " is processing"
        else:
            message += f" status: {task.status}"

        # Safely format timestamp
        timestamp = ""
        if task.created_at:
            try:
                timestamp = task.created_at.strftime("%H:%M:%S")
            except Exception:
                timestamp = ""
        status_display = task.status.upper() if task.status else "UNKNOWN"

        history_entries.append({
            "time": timestamp,
            "status": status_display,
            "message": message
        })

    return DashboardHistoryResponse(status="success", data=history_entries)


@router_dashboard.get("/dashboard/project", response_model=DashboardProjectResponse)
async def get_dashboard_project(
    db: AsyncSession = Depends(get_db)
) -> DashboardProjectResponse:
    """
    Return default project address and jurisdiction info.
    Uses the most common jurisdiction from code references.
    """
    jurisdiction_stmt = select(
        CodeReference.jurisdiction,
        func.count().label("count")
    ).group_by(CodeReference.jurisdiction).order_by(desc("count")).limit(1)
    result = await db.execute(jurisdiction_stmt)
    row = result.first()
    jurisdiction = row.jurisdiction if row else ""

    # No project address table, so return empty string
    address = ""

    data = {
        "address": address,
        "jurisdiction": jurisdiction
    }
    return DashboardProjectResponse(status="success", data=data)


@router_dashboard.get("/dashboard/codes", response_model=DashboardCodesResponse)
async def get_dashboard_codes(
    db: AsyncSession = Depends(get_db)
) -> DashboardCodesResponse:
    """
    Return a list of active code references from the database.
    Filters out any records that appear to be file artifacts (e.g., containing '[ARCHITECTURAL]' or similar).
    """
    # Query CodeReference, but exclude records that have patterns typical of uploaded files
    # We'll assume valid codes have section that doesn't contain brackets or file extensions
    stmt = select(CodeReference)
    # Add filter to exclude suspicious patterns
    stmt = stmt.where(
        ~CodeReference.section.ilike('%[ARCHITECTURAL]%')
    ).where(
        ~CodeReference.section.ilike('%.pdf')
    ).where(
        ~CodeReference.section.ilike('%.jpg')
    ).where(
        ~CodeReference.section.ilike('%.png')
    ).limit(20)

    result = await db.execute(stmt)
    codes = result.scalars().all()

    code_list = []
    for code in codes:
        code_list.append({
            "code_id": code.section,
            "title": code.title or code.description or "No title",
            "severity": code.severity or "active",
            "jurisdiction": code.jurisdiction
        })

    return DashboardCodesResponse(status="success", data=code_list)


@router_dashboard.post("/dashboard/verify-address", response_model=VerifyAddressResponse)
async def verify_address(
    request: VerifyAddressRequest,
    db: AsyncSession = Depends(get_db)
) -> VerifyAddressResponse:
    """
    Verify a project address, determine jurisdiction dynamically,
    and return coverage stats based on actual database counts.
    """
    address = request.address.strip()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address cannot be empty."
        )

    # Get all distinct jurisdictions
    jurisdiction_stmt = select(CodeReference.jurisdiction).distinct()
    result = await db.execute(jurisdiction_stmt)
    jurisdictions = [row[0] for row in result.all() if row[0]]

    # Detect jurisdiction from address (case-insensitive)
    detected_jurisdiction = ""
    address_lower = address.lower()
    for j in jurisdictions:
        if j.lower() in address_lower:
            detected_jurisdiction = j
            break

    # If no match, fallback to most common jurisdiction
    if not detected_jurisdiction and jurisdictions:
        # Get most frequent
        freq_stmt = select(
            CodeReference.jurisdiction,
            func.count().label("cnt")
        ).group_by(CodeReference.jurisdiction).order_by(desc("cnt")).limit(1)
        freq_result = await db.execute(freq_stmt)
        freq_row = freq_result.first()
        detected_jurisdiction = freq_row.jurisdiction if freq_row else ""

    # Count codes for detected jurisdiction
    code_count = 0
    regulation_count = 0
    law_count = 0
    coverage_percentage = 0

    if detected_jurisdiction:
        # Total codes for this jurisdiction
        stmt = select(func.count()).select_from(CodeReference).where(
            CodeReference.jurisdiction == detected_jurisdiction
        )
        code_count = (await db.execute(stmt)).scalar() or 0

        # Count distinct code types for this jurisdiction
        type_stmt = select(
            CodeReference.code_type,
            func.count().label("cnt")
        ).where(
            CodeReference.jurisdiction == detected_jurisdiction
        ).group_by(CodeReference.code_type)
        type_result = await db.execute(type_stmt)
        type_counts = {row.code_type: row.cnt for row in type_result.all()}

        # Map code_type to regulations and laws (heuristic)
        # Example: 'building' -> code, 'fire' -> regulation, 'safety' -> law
        regulation_count = type_counts.get("fire", 0) + type_counts.get("safety", 0)
        law_count = type_counts.get("law", 0)

        # Coverage percentage: proportion of codes in this jurisdiction vs total
        total_codes_stmt = select(func.count()).select_from(CodeReference)
        total_codes = (await db.execute(total_codes_stmt)).scalar() or 1
        coverage_percentage = min(100, int((code_count / total_codes) * 100))

    has_codes = code_count > 0

    response_data = {
        "jurisdiction": detected_jurisdiction,
        "code_count": code_count,
        "regulation_count": regulation_count,
        "law_count": law_count,
        "coverage_percentage": coverage_percentage,
        "has_codes": has_codes
    }

    return VerifyAddressResponse(status="success", data=response_data)


# ================================================================
# Combined Router for export
# ================================================================
router = APIRouter()
router.include_router(router_v1)
router.include_router(router_dashboard)
