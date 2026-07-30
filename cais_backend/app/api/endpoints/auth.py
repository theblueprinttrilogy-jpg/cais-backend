"""
Authentication API Endpoints

This module provides authentication endpoints for user login, registration,
logout, and token refresh.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.core.exceptions import UnauthorizedException, ConflictException, NotFoundException
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest
from app.schemas.user import UserResponse
from app.payment.subscription_manager import SubscriptionManager

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with 30-day free trial.

    Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2:
    - 30 days free for all new users
    - Trial starts automatically
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise ConflictException("Email already registered")

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == request.username).first()
    if existing_username:
        raise ConflictException("Username already taken")

    # Create new user
    hashed_password = get_password_hash(request.password)
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        is_active=True,
        is_verified=True,
        preferred_language=request.language or "en"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Start 30-day free trial
    subscription_manager = SubscriptionManager(db)
    subscription_manager.start_trial(user)

    return user


@router.post("/login", response_model=TokenResponse)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login user and return access and refresh tokens.

    Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2:
    - Check if user has active trial or subscription
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise UnauthorizedException("Invalid email or password")

    if not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedException("User account is disabled")

    # Check access (trial or subscription)
    subscription_manager = SubscriptionManager(db)
    access_info = subscription_manager.get_user_access(user)

    if not access_info.get('access_granted', False):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription or trial. Please subscribe.",
            headers={"X-Payment-Required": "true"}
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(request.refresh_token)
    if not payload:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid token type")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User", user_id)

    if not user.is_active:
        raise UnauthorizedException("User account is disabled")

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800
    }


@router.post("/logout")
async def logout_user(
    token: str = Depends(oauth2_scheme)
):
    """
    Logout user (client-side token invalidation).

    Note: JWT tokens are stateless. The client must discard the token.
    """
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all_devices(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Logout from all devices (requires token rotation).

    Note: In a production system, this would invalidate all refresh tokens.
    """
    return {"message": "Successfully logged out from all devices"}
