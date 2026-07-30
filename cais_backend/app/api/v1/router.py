"""
API v1 Router - Main Router for Version 1

This module aggregates all v1 API routes.
"""

from fastapi import APIRouter

# Import endpoints
from app.api.endpoints import (
    auth, users, projects, upload, analysis, reports,
    payments, subscriptions, webhooks, kill_switch,
    dashboard, notifications, metrics, admin, tasks
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Users
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Projects
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Upload
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])

# Analysis
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# Reports
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# Payments
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])

# Subscriptions
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])

# Webhooks
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# Kill Switch
api_router.include_router(kill_switch.router, prefix="/kill", tags=["kill"])

# Dashboard
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Notifications
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

# Metrics
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

# Admin
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Tasks
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])


@api_router.get("/ping")
async def ping():
    """Health check for API v1."""
    return {"status": "pong", "version": "v1", "timestamp": "2026-07-30"}
