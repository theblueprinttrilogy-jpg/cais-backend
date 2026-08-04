"""
CAIS Code Compliance API - Main Application Entry Point.

This module initializes the FastAPI application, configures CORS,
includes all routers, mounts static files, sets up Jinja2 templates,
and defines the dashboard endpoints with precise context variables.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.auth import router as auth_router
from app.api.endpoints import router as endpoints_router
from app.routers.forensic_compliance import router as forensic_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("CAIS Code Compliance API starting up...")
    yield
    # Shutdown
    logger.info("CAIS Code Compliance API shutting down...")


# Initialize FastAPI application
app = FastAPI(
    title="CAIS Code Compliance API",
    description="Forensic compliance, semantic search, and deterministic audit for construction plans.",
    version="10.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(endpoints_router)
app.include_router(forensic_router)

# Mount static files
app.mount("/static", StaticFiles(directory="app/skins/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/skins/templates")


# Dashboard route
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """
    Render the CAIS dashboard with the exact context variables expected by dashboard.html.
    """
    context = {
        "request": request,
        "total_projects": 42,
        "total_documents": 156,
        "total_violations": 23,
        "compliance_rate": 87,
        "recent_activities": [
            {"timestamp": "2 min ago", "type": "upload", "message": "Plan R-2024-001 uploaded"},
            {"timestamp": "15 min ago", "type": "audit", "message": "Forensic audit completed for building B"},
            {"timestamp": "1 hour ago", "type": "alert", "message": "Fire exit clearance violation detected"},
            {"timestamp": "3 hours ago", "type": "upload", "message": "Revised HVAC schematics uploaded"},
        ],
        "critical_count": 5,
        "critical_percent": 22,
        "high_count": 8,
        "high_percent": 35,
        "medium_count": 7,
        "medium_percent": 30,
        "low_count": 3,
        "low_percent": 13,
    }
    return templates.TemplateResponse("dashboard.html", context)


# Root endpoint redirects to dashboard
@app.get("/", response_class=RedirectResponse)
async def root() -> RedirectResponse:
    """
    Redirect root to dashboard.
    """
    return RedirectResponse(url="/dashboard", status_code=302)


# Health check endpoint
@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for container orchestration and monitoring.
    """
    return {"status": "healthy"}
