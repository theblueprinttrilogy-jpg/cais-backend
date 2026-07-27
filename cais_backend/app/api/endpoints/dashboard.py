from fastapi import APIRouter, HTTPException, status
import json
import os
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

def get_drive_service():
    """Helper to safely initialize Google Drive client if configured."""
    creds_json = getattr(settings, "GCP_CREDENTIALS_JSON", None)
    if not creds_json:
        logger.warning("GCP_CREDENTIALS_JSON is not configured or empty.")
        return None
    try:
        if os.path.exists(creds_json):
            with open(creds_json, "r") as f:
                info = json.load(f)
        else:
            info = json.loads(creds_json)
        return info
    except Exception as e:
        logger.warning("Failed to parse Google Drive credentials: %s", e)
        return None

@router.get("/jurisdiction/{zip_code}")
async def get_jurisdiction_dashboard(zip_code: str):
    """
    Dashboard endpoint to query jurisdiction and requirements by ZIP code.
    """
    try:
        return {
            "zip_code": zip_code,
            "jurisdiction": "Default Jurisdiction",
            "requirements": [
                "OSHA Compliance Standard 1926",
                "Local Building Code Verification"
            ],
            "status": "active"
        }
    except Exception as e:
        logger.exception("Error fetching jurisdiction dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
