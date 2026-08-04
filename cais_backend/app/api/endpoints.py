"""
app/api/endpoints.py

FastAPI endpoints for CAIS Code Compliance backend.
Provides semantic search, deterministic compliance audit, and file upload
for construction documents.
"""

import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

# Import database and model from orchestrator
# Note: CodeReference is expected to be a SQLAlchemy model with embedding support.
from app.agents.orchestrator import CodeReference, SessionLocal
from app.models.agent import AgentTask

logger = logging.getLogger(__name__)

# Initialize the embedding model (same as used in StorageAgent)
MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(MODEL_NAME)

router = APIRouter(prefix="/api/v1", tags=["code-compliance"])


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
    similarity: float  # Cosine similarity (1 = most similar)


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str
    results: List[SearchResultItem]


class AuditRequest(BaseModel):
    """Request model for compliance audit."""
    jurisdiction: str = Field(..., description="Jurisdiction (e.g., 'US', 'CA')")
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
    required: bool = True  # Always True for violations


class AuditResponse(BaseModel):
    """Response model for audit endpoint."""
    jurisdiction: str
    code_type: str
    total_required_sections: int
    compliant_sections_count: int
    violations: List[ViolationItem]
    total_violations: int
    status: str  # "compliant" or "non-compliant"


class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    task_id: str
    status: str
    message: Optional[str] = None


# -------------------- Dependency --------------------

def get_db() -> Session:
    """Provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- Helper Functions --------------------

def validate_pdf(filename: str) -> bool:
    """Check if the uploaded file has a .pdf extension."""
    return filename.lower().endswith(".pdf")


def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Save an uploaded file to a given destination path."""
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


# -------------------- Endpoints --------------------

@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db)
) -> SearchResponse:
    """
    Perform semantic vector similarity search over code references.

    The input query is embedded using the same SentenceTransformer model,
    and the nearest neighbors in the embedding space are returned with
    cosine similarity scores.
    """
    logger.info(f"Semantic search query: '{request.query}'")

    # Generate embedding for the query
    query_embedding = embedding_model.encode(request.query, normalize_embeddings=True).tolist()

    # Use pgvector's cosine distance operator (<->) to find nearest neighbors
    # The closer to 1, the more similar (since we used normalize_embeddings=True,
    # cosine distance = 1 - cosine_similarity, so we order by distance ascending
    # and compute similarity as 1 - distance.
    results = db.query(
        CodeReference,
        (1 - CodeReference.embedding.cosine_distance(query_embedding)).label("similarity")
    ).order_by(
        CodeReference.embedding.cosine_distance(query_embedding)
    ).limit(request.limit).all()

    # Build response items
    items = []
    for ref, similarity in results:
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


@router.post("/audit", response_model=AuditResponse)
async def compliance_audit(
    request: AuditRequest,
    db: Session = Depends(get_db)
) -> AuditResponse:
    """
    Perform a deterministic compliance audit.

    Given a jurisdiction, code type, and a list of sections the building
    claims to comply with, this endpoint determines which required sections
    (present in the database for that jurisdiction and code type) are not
    met. Returns a list of violations and a compliance status.
    """
    logger.info(
        f"Audit request: jurisdiction={request.jurisdiction}, "
        f"code_type={request.code_type}, compliant_sections={request.compliant_sections}"
    )

    # Fetch all required sections for the given jurisdiction and code_type
    required_refs = db.query(CodeReference).filter_by(
        jurisdiction=request.jurisdiction,
        code_type=request.code_type
    ).all()

    if not required_refs:
        # No regulations found; consider compliant by default
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

    # Build a set of compliant sections for fast lookup
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
    status = "compliant" if len(violations) == 0 else "non-compliant"

    logger.info(f"Audit complete: {len(violations)} violations found.")
    return AuditResponse(
        jurisdiction=request.jurisdiction,
        code_type=request.code_type,
        total_required_sections=total_required,
        compliant_sections_count=compliant_count,
        violations=violations,
        total_violations=len(violations),
        status=status
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(..., description="Construction document PDF"),
    db: Session = Depends(get_db)
) -> UploadResponse:
    """
    Upload a construction document PDF for processing.

    The file is validated to be a PDF, saved to a temporary location,
    and a task is created for background OCR/PlanInspector processing.
    Returns a task_id that can be used to poll the task status.
    """
    logger.info(f"Received upload: filename={file.filename}")

    # Validate file extension
    if not validate_pdf(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed."
        )

    # Generate a unique task ID and a temporary file path
    task_id = str(uuid.uuid4())
    temp_dir = "/tmp/cais_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{task_id}.pdf")

    try:
        # Save the uploaded file to a temporary location
        save_upload_file(file, temp_file_path)
        logger.info(f"File saved to {temp_file_path}")

        # Create a task record in the database for background processing
        # The agent_name "ingestion" is assumed to be registered in the orchestrator.
        # The input_data stores the file path and original filename.
        task = AgentTask(
            id=task_id,
            agent_name="ingestion",  # This must match the agent name used by the worker
            status="pending",
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
        db.commit()
        db.refresh(task)

        logger.info(f"Task {task_id} created for file {file.filename}")

        return UploadResponse(
            task_id=task_id,
            status="processing",
            message="File accepted. Processing will begin shortly."
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        # Clean up partially saved file if any
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload."
        )


# Optional: health check endpoint
@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

