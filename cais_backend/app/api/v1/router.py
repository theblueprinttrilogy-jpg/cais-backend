"""
CAIS Code Compliance - API v1 Router

This module aggregates all endpoint routers for version 1 of the API.
Each router is included with appropriate tags for documentation grouping.
"""

from fastapi import APIRouter

# Import all endpoint routers
from app.api.v1.endpoints import (
    auth,
    users,
    projects,
    analysis,
    reports,
    payments,
    subscriptions,
    webhooks,
    kill_switch,
    dashboard,
    ping,
    upload,
)

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers with descriptive tags
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(payments.router, tags=["payments"])
api_router.include_router(subscriptions.router, tags=["subscriptions"])
api_router.include_router(webhooks.router, tags=["webhooks"])
api_router.include_router(kill_switch.router, tags=["kill_switch"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(ping.router, tags=["ping"])

# Upload router already defines its own prefix ("/upload") in its module,
# so we include it without an additional prefix to avoid duplication.
api_router.include_router(upload.router, tags=["upload"])
