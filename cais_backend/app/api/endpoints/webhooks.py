"""
Webhooks API Endpoints

This module provides webhook endpoints for external platform integrations
including Procore, SharePoint, Dropbox, and other marketplaces.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 1.1
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.document import Document
from app.models.project import Project
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/procore")
async def procore_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Procore integration.

    Receives document updates from Procore platform.
    """
    try:
        body = await request.json()
        logger.info(f"Procore webhook received: {body.get('event', 'unknown')}")

        # Verify webhook signature (in production)
        # signature = request.headers.get("X-Procore-Signature")

        event_type = body.get('event', '')
        data = body.get('data', {})

        if event_type == 'document.uploaded':
            # Process document upload from Procore
            document_data = {
                'filename': data.get('filename', 'unknown'),
                'file_url': data.get('url', ''),
                'project_id': data.get('project_id', ''),
                'user_id': data.get('user_id', '')
            }
            logger.info(f"Procore document uploaded: {document_data['filename']}")

        return {"status": "received", "event": event_type}

    except Exception as e:
        logger.error(f"Procore webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sharepoint")
async def sharepoint_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for SharePoint integration.

    Receives document updates from SharePoint/Graph API.
    """
    try:
        body = await request.json()
        logger.info(f"SharePoint webhook received: {body.get('eventType', 'unknown')}")

        event_type = body.get('eventType', '')
        data = body.get('value', {})

        if event_type == 'file.created' or event_type == 'file.updated':
            # Process file from SharePoint
            file_data = {
                'filename': data.get('name', 'unknown'),
                'file_url': data.get('webUrl', ''),
                'site_id': data.get('siteId', ''),
                'list_id': data.get('listId', '')
            }
            logger.info(f"SharePoint file event: {file_data['filename']}")

        return {"status": "received", "event": event_type}

    except Exception as e:
        logger.error(f"SharePoint webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dropbox")
async def dropbox_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Dropbox integration.

    Receives file updates from Dropbox API.
    """
    try:
        body = await request.json()
        logger.info(f"Dropbox webhook received")

        # Dropbox webhook verification
        challenge = request.query_params.get('challenge')
        if challenge:
            return {"challenge": challenge}

        # Process file events
        delta = body.get('delta', {})
        entries = delta.get('entries', [])

        for entry in entries:
            path = entry.get('path', '')
            logger.info(f"Dropbox file event: {path}")

        return {"status": "received"}

    except Exception as e:
        logger.error(f"Dropbox webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google-drive")
async def google_drive_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Google Drive integration.

    Receives file updates from Google Drive API.
    """
    try:
        body = await request.json()
        logger.info(f"Google Drive webhook received")

        event_type = body.get('event', '')
        data = body.get('data', {})

        if event_type == 'file.uploaded':
            file_data = {
                'filename': data.get('name', 'unknown'),
                'file_id': data.get('id', ''),
                'mime_type': data.get('mimeType', '')
            }
            logger.info(f"Google Drive file uploaded: {file_data['filename']}")

        return {"status": "received", "event": event_type}

    except Exception as e:
        logger.error(f"Google Drive webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generic")
async def generic_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Generic webhook endpoint for other platform integrations.
    """
    try:
        body = await request.json()
        platform = request.headers.get("X-Platform", "unknown")
        logger.info(f"Generic webhook from {platform}")

        return {"status": "received", "platform": platform}

    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{platform}")
async def verify_webhook(
    platform: str,
    request: Request
):
    """
    Verify webhook endpoint for platform configuration.
    """
    logger.info(f"Webhook verification for platform: {platform}")
    return {"status": "verified", "platform": platform}
