"""
app/api/endpoints.py

FastAPI endpoints for CAIS Code Compliance backend.
Provides semantic search and deterministic compliance audit capabilities.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

# Import database and model from orchestrator
from app.agents.orchestrator import CodeReference, SessionLocal

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


# -------------------- Dependency --------------------

def get_db() -> Session:
    """Provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# Optional: health check endpoint
@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
