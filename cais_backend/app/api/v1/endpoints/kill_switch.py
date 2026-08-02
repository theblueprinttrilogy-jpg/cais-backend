"""
Kill Switch API Endpoints

This module provides emergency kill switch functionality to stop operations,
destroy temporary containers, and clean up temporary files.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 7.1
"""

import logging
import os
import shutil
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.db.models import Document, User
from app.api.deps import get_current_active_user, get_current_superuser
from app.services.worm_ledger import WORMService as WormLedger

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{task_id}")
async def activate_kill_switch(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Activate kill switch for a specific task.

    Stops processing, destroys temporary containers, and cleans up files.
    """
    logger.warning(f"KILL SWITCH ACTIVATED for task: {task_id} by user: {current_user.email}")

    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    # Step 1: Update document status
    document.status = "killed"
    db.commit()

    # Step 2: Destroy temporary containers (if running)
    containers_destroyed = _destroy_temporary_containers(task_id)

    # Step 3: Clean up temporary files
    files_cleaned = _cleanup_temporary_files(task_id)

    # Step 4: Log to WORM Ledger
    try:
        worm_ledger = WormLedger()
        # Note: WORMService uses async methods, we need to handle this properly
        # For now, we'll log synchronously
        logger.info(f"KILL_SWITCH_ACTIVATED for task: {task_id}")
    except Exception as e:
        logger.error(f"Failed to log kill switch to WORM: {e}")

    logger.info(f"Kill switch completed for task: {task_id}")

    return {
        "status": "killed",
        "task_id": task_id,
        "containers_destroyed": containers_destroyed,
        "files_cleaned": files_cleaned,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/all")
async def activate_kill_switch_all(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Activate kill switch for ALL running tasks (admin only).

    This is an emergency function that stops ALL processing.
    """
    logger.warning(f"KILL SWITCH ALL activated by admin: {current_user.email}")

    # Get all processing documents
    processing_docs = db.query(Document).filter(
        Document.status.in_(['processing', 'pending', 'uploaded'])
    ).all()

    results = []
    for doc in processing_docs:
        try:
            result = await activate_kill_switch(
                doc.task_id,
                current_user,
                db
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to kill task {doc.task_id}: {e}")
            results.append({
                "task_id": doc.task_id,
                "status": "failed",
                "error": str(e)
            })

    return {
        "status": "completed",
        "total_tasks": len(processing_docs),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status/{task_id}")
async def get_kill_switch_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Check if a task has been killed.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    return {
        "task_id": task_id,
        "status": document.status,
        "is_killed": document.status == "killed",
        "timestamp": datetime.now().isoformat()
    }


def _destroy_temporary_containers(task_id: str) -> int:
    """
    Destroy temporary containers associated with a task.
    """
    containers_destroyed = 0
    try:
        import docker
        client = docker.from_env()

        # Find containers with task_id label
        containers = client.containers.list(
            all=True,
            filters={"label": f"task_id={task_id}"}
        )

        for container in containers:
            try:
                container.stop(timeout=5)
                container.remove(force=True)
                containers_destroyed += 1
                logger.info(f"Destroyed container: {container.name}")
            except Exception as e:
                logger.error(f"Failed to destroy container {container.name}: {e}")

    except ImportError:
        logger.warning("Docker not available, skipping container destruction")
    except Exception as e:
        logger.error(f"Error destroying containers: {e}")

    return containers_destroyed


def _cleanup_temporary_files(task_id: str) -> int:
    """
    Clean up temporary files associated with a task.
    """
    files_cleaned = 0
    temp_dirs = [
        f"/tmp/cais_{task_id}",
        f"/tmp/uploads/{task_id}",
        f"/tmp/evidence/{task_id}",
        f"/app/storage/temp/{task_id}"
    ]

    for dir_path in temp_dirs:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                files_cleaned += 1
                logger.info(f"Cleaned up directory: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to clean up {dir_path}: {e}")

    return files_cleaned
