"""
Project Schemas - Pydantic Models for Project Endpoints

This module contains Pydantic schemas for project management.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str
    address: Optional[str] = None
    jurisdiction: Optional[str] = None
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    pass


class ProjectUpdate(BaseModel):
    """Project update schema."""
    name: Optional[str] = None
    address: Optional[str] = None
    jurisdiction: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Project response schema."""
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
