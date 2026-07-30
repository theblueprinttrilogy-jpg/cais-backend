"""
WORM Entry Model - Backward Compatibility

This file exists for backward compatibility.
The actual model is defined in app/db/models.py
"""

from app.db.models import WORMLedgerEntry

__all__ = ["WORMLedgerEntry"]
