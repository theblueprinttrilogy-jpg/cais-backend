"""
Users API Endpoints

This module provides user management endpoints for CRUD operations.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException, ConflictException
from app.db.models import User
from app.schemas.user import UserResponse, UserUpdate
from app.api.deps import get_current_active_user, get_current_superuser

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current user's information.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's information.
    """
    if user_update.email and user_update.email != current_user.email:
        existing = db.query(User).filter(User.email == user_update.email).first()
        if existing:
            raise ConflictException("Email already registered")

    if user_update.username and user_update.username != current_user.username:
        existing = db.query(User).filter(User.username == user_update.username).first()
        if existing:
            raise ConflictException("Username already taken")

    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Get a user by ID (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User", user_id)
    return user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete a user (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User", user_id)

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return None
