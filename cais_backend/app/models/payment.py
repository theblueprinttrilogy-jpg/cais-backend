"""
Payment Model - Backward Compatibility

This file exists for backward compatibility.
The actual model is defined in app/db/models.py
"""

from app.db.models import Payment

__all__ = ["Payment"]
