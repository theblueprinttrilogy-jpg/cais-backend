"""
Permissions Core - Role-Based Access Control

This module provides role-based access control utilities.
"""

from typing import List, Optional
from functools import wraps
from fastapi import HTTPException, status

from app.db.models import User


class Permission:
    """
    Permission class for RBAC.
    """

    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"

    # Document permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"

    # Analysis permissions
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_RUN = "analysis:run"

    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"


class Role:
    """
    Role class with associated permissions.
    """

    # Predefined roles
    ROLES = {
        "admin": [
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.USER_DELETE,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_DELETE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_WRITE,
            Permission.DOCUMENT_DELETE,
            Permission.ANALYSIS_READ,
            Permission.ANALYSIS_RUN,
            Permission.ADMIN_READ,
            Permission.ADMIN_WRITE,
            Permission.ADMIN_DELETE,
        ],
        "user": [
            Permission.USER_READ,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_WRITE,
            Permission.ANALYSIS_READ,
            Permission.ANALYSIS_RUN,
        ],
        "guest": [
            Permission.USER_READ,
            Permission.PROJECT_READ,
            Permission.DOCUMENT_READ,
        ],
    }

    def __init__(self, name: str):
        self.name = name
        self.permissions = self.ROLES.get(name, [])

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions


def get_user_role(user: User) -> str:
    """
    Get role for a user.

    Args:
        user: User object

    Returns:
        str: Role name
    """
    if user.is_superuser:
        return "admin"
    return "user"


def require_permission(permission: str):
    """
    Decorator to require a specific permission.

    Usage:
        @require_permission(Permission.PROJECT_WRITE)
        async def create_project(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if user is in kwargs
            user = kwargs.get("current_user")
            if not user:
                # Check if user is in args
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            role = get_user_role(user)
            role_obj = Role(role)

            if not role_obj.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def has_permission(user: User, permission: str) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user: User object
        permission: Permission to check

    Returns:
        bool: True if user has permission
    """
    role = get_user_role(user)
    role_obj = Role(role)
    return role_obj.has_permission(permission)
