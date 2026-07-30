"""
Schemas Package - Pydantic Models for API Validation

This package contains all Pydantic schemas for request/response validation.
"""

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.subscription import PlanResponse, SubscriptionResponse, SubscriptionUpdate
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWebhook
from app.schemas.analysis import (
    AnalysisStatus, AnalysisResult, AnalysisStartRequest,
    AnalysisStartResponse, ViolationResponse
)
from app.schemas.report import ReportResponse, ReportStatusResponse, ReportDownloadResponse
from app.schemas.response import (
    APIResponse, PaginatedResponse, ErrorResponse,
    HealthResponse, MessageResponse
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    # User
    "UserResponse",
    "UserCreate",
    "UserUpdate",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    # Subscription
    "PlanResponse",
    "SubscriptionResponse",
    "SubscriptionUpdate",
    # Payment
    "PaymentCreate",
    "PaymentResponse",
    "PaymentWebhook",
    # Analysis
    "AnalysisStatus",
    "AnalysisResult",
    "AnalysisStartRequest",
    "AnalysisStartResponse",
    "ViolationResponse",
    # Report
    "ReportResponse",
    "ReportStatusResponse",
    "ReportDownloadResponse",
    # Response
    "APIResponse",
    "PaginatedResponse",
    "ErrorResponse",
    "HealthResponse",
    "MessageResponse",
]
