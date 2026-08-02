"""
Webhooks API Endpoints

This module provides webhook endpoints for external platform integrations
including Procore, SharePoint, Dropbox, Google Drive, and generic webhooks.

Each webhook validates incoming requests, processes events, and logs
to the WORM Ledger for immutable audit trail.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 1.1
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ValidationException
from app.db.models import Document, Project, User
from app.agents.worm_ledger import WormLedger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/procore")
async def procore_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Webhook endpoint for Procore integration.

    Receives document updates from Procore platform.
    Events handled: document.uploaded, document.updated, etc.

    In production, verify the X-Procore-Signature header.
    """
    try:
        body = await request.json()
        event_type = body.get('event', 'unknown')
        data = body.get('data', {})
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        filename = data.get('filename', 'unknown')
        file_url = data.get('url', '')

        logger.info(f"Procore webhook received: {event_type} from project {project_id}")

        # In production, verify signature:
        # signature = request.headers.get("X-Procore-Signature")
        # if not verify_procore_signature(signature, body):
        #     raise HTTPException(status_code=401, detail="Invalid signature")

        # Process event
        if event_type in ['document.uploaded', 'document.updated']:
            # Here we would trigger document processing
            # For now, just log and record in WORM
            worm_ledger = WormLedger(db)
            worm_ledger.record_action(
                action=f'PROCORE_{event_type.upper()}',
                data={
                    'project_id': project_id,
                    'user_id': user_id,
                    'filename': filename,
                    'file_url': file_url,
                    'event_type': event_type
                },
                user_id=user_id
            )

            logger.info(f"Procore document event: {filename}")

        return {"status": "received", "event": event_type}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Procore webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sharepoint")
async def sharepoint_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Webhook endpoint for SharePoint / Microsoft Graph integration.

    Receives file updates from SharePoint/Graph API.
    Events handled: file.created, file.updated, file.deleted.

    Requires validation of the webhook subscription in production.
    """
    try:
        body = await request.json()
        event_type = body.get('eventType', 'unknown')
        data = body.get('value', {})
        site_id = data.get('siteId', '')
        list_id = data.get('listId', '')
        filename = data.get('name', 'unknown')
        file_url = data.get('webUrl', '')

        logger.info(f"SharePoint webhook received: {event_type} from site {site_id}")

        # Process event
        if event_type in ['file.created', 'file.updated']:
            worm_ledger = WormLedger(db)
            worm_ledger.record_action(
                action=f'SHAREPOINT_{event_type.upper()}',
                data={
                    'site_id': site_id,
                    'list_id': list_id,
                    'filename': filename,
                    'file_url': file_url,
                    'event_type': event_type
                },
                user_id=None  # SharePoint events may not include user ID
            )

            logger.info(f"SharePoint file event: {filename}")

        return {"status": "received", "event": event_type}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"SharePoint webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dropbox")
async def dropbox_webhook(
    request: Request,
    db: Session = Depends(get_db),
    challenge: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Webhook endpoint for Dropbox integration.

    Dropbox sends a 'challenge' parameter for verification during setup.
    For regular events, it sends a delta with file entries.

    Docs: https://www.dropbox.com/developers/reference/webhooks
    """
    try:
        # Handle verification challenge
        if challenge:
            logger.info("Dropbox webhook verification challenge received")
            return {"challenge": challenge}

        # Process regular events
        body = await request.json()
        logger.info("Dropbox webhook received with delta")

        # Dropbox sends delta with entries
        delta = body.get('delta', {})
        entries = delta.get('entries', [])

        worm_ledger = WormLedger(db)

        for entry in entries:
            path = entry.get('path', '')
            entry_type = 'file' if not path.endswith('/') else 'folder'

            if entry_type == 'file':
                worm_ledger.record_action(
                    action='DROPBOX_FILE_EVENT',
                    data={
                        'path': path,
                        'event_type': 'changed'
                    },
                    user_id=None
                )
                logger.info(f"Dropbox file event: {path}")

        # Dropbox may also send 'users' and 'accounts' fields
        # We only process file events for now

        return {"status": "received"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Dropbox webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google-drive")
async def google_drive_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Webhook endpoint for Google Drive integration.

    Receives file updates from Google Drive API via push notifications.
    Events: file.uploaded, file.updated, file.trashed, etc.

    In production, verify the X-Goog-Resource-State header.
    """
    try:
        body = await request.json()
        event_type = body.get('event', 'unknown')
        data = body.get('data', {})
        file_id = data.get('id', '')
        filename = data.get('name', 'unknown')
        mime_type = data.get('mimeType', '')

        logger.info(f"Google Drive webhook received: {event_type} for file {file_id}")

        # In production, verify:
        # resource_state = request.headers.get("X-Goog-Resource-State")
        # channel_id = request.headers.get("X-Goog-Channel-ID")

        if event_type in ['file.uploaded', 'file.updated']:
            worm_ledger = WormLedger(db)
            worm_ledger.record_action(
                action=f'GOOGLEDRIVE_{event_type.upper()}',
                data={
                    'file_id': file_id,
                    'filename': filename,
                    'mime_type': mime_type,
                    'event_type': event_type
                },
                user_id=None
            )

            logger.info(f"Google Drive file event: {filename}")

        return {"status": "received", "event": event_type}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Google Drive webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generic")
async def generic_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generic webhook endpoint for other platform integrations.

    Accepts any JSON payload and logs it to WORM Ledger.
    Platform can be identified via X-Platform header.
    """
    try:
        body = await request.json()
        platform = request.headers.get("X-Platform", "unknown")
        event_type = request.headers.get("X-Event-Type", "generic")

        logger.info(f"Generic webhook received from {platform}: {event_type}")

        worm_ledger = WormLedger(db)
        worm_ledger.record_action(
            action=f'WEBHOOK_{platform.upper()}',
            data={
                'platform': platform,
                'event_type': event_type,
                'payload': body
            },
            user_id=None
        )

        return {"status": "received", "platform": platform, "event": event_type}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{platform}")
async def verify_webhook(
    platform: str,
    request: Request
) -> Dict[str, Any]:
    """
    Verification endpoint for webhook configuration.

    Used by platforms to validate that the webhook URL is active.
    """
    logger.info(f"Webhook verification for platform: {platform}")
    return {"status": "verified", "platform": platform, "timestamp": datetime.utcnow().isoformat()}
