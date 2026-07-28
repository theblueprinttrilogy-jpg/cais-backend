# app/main.py - CAIS v2.0 Main Application Entry Point
# Production-ready FastAPI application with integrated SemanticEngine,
# auto-healing telemetry endpoint, and graceful lifecycle management.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# Import SemanticEngine from core semantic module
from app.core.semantic.engine import SemanticEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Lifespan Management
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic for the FastAPI application.
    Initializes the SemanticEngine on startup and ensures graceful shutdown.
    """
    # ---- Startup ----
    logger.info("Starting CAIS v2.0 application...")
    # Initialize the SemanticEngine with production settings
    # (can be configured via environment variables or config)
    semantic_engine = SemanticEngine(
        dict_dir="semantic_dictionaries",  # Adjust as needed
        block_on_missing=False,
        max_block_wait=0.5,
        hydration_threads=8,
    )
    app.state.semantic_engine = semantic_engine
    logger.info("SemanticEngine initialized and attached to app.state.")

    yield  # Application runs here

    # ---- Shutdown ----
    logger.info("Shutting down CAIS v2.0 application...")
    if hasattr(app.state, "semantic_engine"):
        app.state.semantic_engine.shutdown()
        logger.info("SemanticEngine shut down gracefully.")

# ------------------------------------------------------------------------------
# FastAPI Application
# ------------------------------------------------------------------------------
app = FastAPI(
    title="CAIS v2.0 - Compliance Auditing & Testing System",
    description="Semantic engine for multilingual building code analysis with auto-healing.",
    version="2.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# Health & Telemetry Endpoints
# ------------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint for basic health check."""
    return {"status": "ok", "service": "CAIS v2.0", "version": "2.0.0"}

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy"}

@app.get("/api/v1/semantic/metrics")
async def semantic_metrics(request: Request):
    """
    Expose auto-healing telemetry and scaling signals from the SemanticEngine.
    Returns:
        - Lookup statistics (counts, latency distribution)
        - Error rates
        - Pool saturation
        - Recommended scaling tier
        - Scale-up required flag
        - Current load level
    """
    engine = getattr(request.app.state, "semantic_engine", None)
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={"error": "SemanticEngine not initialized or unavailable."}
        )
    try:
        metrics = engine.get_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Failed to retrieve semantic metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error while fetching metrics."}
        )

# ------------------------------------------------------------------------------
# Optional: Additional endpoints for demo or testing
# ------------------------------------------------------------------------------
@app.get("/api/v1/semantic/translate")
async def translate(
    request: Request,
    term: str,
    source_lang: str = "en",
    target_lang: str = "es",
    domain: str = "construction"
):
    """
    Translate a term from source language to target language.
    """
    engine = getattr(request.app.state, "semantic_engine", None)
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={"error": "SemanticEngine not available."}
        )
    try:
        result = engine.translate_term(term, source_lang, target_lang, domain)
        return JSONResponse(content={"term": term, "translation": result})
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Translation failed."}
        )

# ------------------------------------------------------------------------------
# Main entry point (for local development)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
