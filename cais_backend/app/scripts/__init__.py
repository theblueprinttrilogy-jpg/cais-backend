"""
app.scripts – Administrative and utility scripts for the CAIS Code Compliance system.

This package provides functions for database initialization, seeding of reference data,
backup operations, temporary file cleanup, and ingestion of real building codes.
All functions are imported here for convenient access from a single entry point.
"""

from app.scripts.init_db import init_database
from app.scripts.seed_data import seed_database
from app.scripts.backup import backup_database
from app.scripts.cleanup import cleanup_temp_files
from app.scripts.ingest_real_codes import ingest_codes

__all__ = [
    "init_database",
    "seed_database",
    "backup_database",
    "cleanup_temp_files",
    "ingest_codes",
]
