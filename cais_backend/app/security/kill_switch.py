"""
Kill Switch API Endpoints - Emergency Stop

This module provides emergency kill switch functionality to stop operations,
destroy temporary containers, and clean up temporary files.

All actions are logged immutably in the WORM Ledger.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 7.1
"""

import logging
import os
import shutil
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.db.models import Document, User
from app.api.deps import get_current_active_user, get_current_superuser
from app.agents.worm_ledger import WormLedger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kill", tags=["kill_switch"])


@router.post("/{task_id}")
async def activate_kill_switch(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Activate kill switch for a specific task.

    Stops processing, destroys temporary containers, and cleans up files.

    Args:
        task_id: Task identifier
        current_user: Authenticated user
        db: Database session

    Returns:
        Status with containers destroyed and files cleaned.
    """
    logger.warning(f"KILL SWITCH ACTIVATED for task: {task_id} by user: {current_user.email}")

    # Find document
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    # Update document status
    document.status = "killed"
    db.commit()

    # Destroy temporary containers
    containers_destroyed = _destroy_temporary_containers(task_id)

    # Clean up temporary files
    files_cleaned = _cleanup_temporary_files(task_id)

    # Log to WORM Ledger
    worm_ledger = WormLedger(db)
    worm_ledger.record_action(
        action='KILL_SWITCH_ACTIVATED',
        data={
            'task_id': task_id,
            'document_id': str(document.id),
            'user_id': str(current_user.id),
            'containers_destroyed': containers_destroyed,
            'files_cleaned': files_cleaned
        },
        user_id=str(current_user.id)
    )

    logger.info(f"Kill switch completed for task: {task_id}")

    return {
        "status": "killed",
        "task_id": task_id,
        "containers_destroyed": containers_destroyed,
        "files_cleaned": files_cleaned,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/all")
async def activate_kill_switch_all(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Activate kill switch for ALL running tasks (admin only).

    This is an emergency function that stops ALL processing.

    Args:
        current_user: Superuser (admin)
        db: Database session

    Returns:
        Summary of all killed tasks.
    """
    if not current_user.is_superuser:
        raise ForbiddenException("Only superusers can activate kill switch for all tasks")

    logger.warning(f"KILL SWITCH ALL activated by admin: {current_user.email}")

    # Get all processing documents
    processing_docs = db.query(Document).filter(
        Document.status.in_(['processing', 'pending', 'uploaded'])
    ).all()

    results = []
    total_containers = 0
    total_files = 0

    for doc in processing_docs:
        try:
            # Simulate async call to the individual kill switch
            # We call the same logic directly to avoid recursion
            doc.status = "killed"
            db.commit()

            containers = _destroy_temporary_containers(doc.task_id)
            files = _cleanup_temporary_files(doc.task_id)

            total_containers += containers
            total_files += files

            results.append({
                "task_id": doc.task_id,
                "status": "killed",
                "containers_destroyed": containers,
                "files_cleaned": files
            })

            # Log to WORM
            worm_ledger = WormLedger(db)
            worm_ledger.record_action(
                action='KILL_SWITCH_ALL',
                data={
                    'task_id': doc.task_id,
                    'document_id': str(doc.id),
                    'admin_user_id': str(current_user.id)
                },
                user_id=str(current_user.id)
            )

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
        "total_containers_destroyed": total_containers,
        "total_files_cleaned": total_files,
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status/{task_id}")
async def get_kill_switch_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if a task has been killed.

    Args:
        task_id: Task identifier
        current_user: Authenticated user
        db: Database session

    Returns:
        Status and killed flag.
    """
    document = db.query(Document).filter(Document.task_id == task_id).first()
    if not document:
        raise NotFoundException("Document", task_id)

    return {
        "task_id": task_id,
        "status": document.status,
        "is_killed": document.status == "killed",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _destroy_temporary_containers(task_id: str) -> int:
    """
    Destroy temporary containers associated with a task.

    Uses Docker API to find containers with label task_id={task_id}
    and removes them forcefully.

    Args:
        task_id: Task identifier

    Returns:
        Number of containers destroyed.
    """
    containers_destroyed = 0
    try:
        import docker
        client = docker.from_env()

        # Find containers with the task_id label
        containers = client.containers.list(
            all=True,
            filters={"label": f"task_id={task_id}"}
        )

        for container in containers:
            try:
                container.stop(timeout=5)
                container.remove(force=True)
                containers_destroyed += 1
                logger.info(f"Destroyed container: {container.name} (ID: {container.id[:12]})")
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

    Removes directories that match the pattern /tmp/*/{task_id} and
    /app/storage/temp/{task_id}.

    Args:
        task_id: Task identifier

    Returns:
        Number of directories cleaned.
    """
    files_cleaned = 0

    # List of possible temp directories
    temp_dirs = [
        f"/tmp/cais_{task_id}",
        f"/tmp/uploads/{task_id}",
        f"/tmp/evidence/{task_id}",
        f"/app/storage/temp/{task_id}",
        f"/app/storage/evidence/temp_{task_id}",
    ]

    for dir_path in temp_dirs:
        if os.path.exists(dir_path):
            try:
                if os.path.isdir(dir_path):
                    shutil.rmtree(dir_path)
                    files_cleaned += 1
                    logger.info(f"Cleaned up directory: {dir_path}")
                else:
                    os.remove(dir_path)
                    files_cleaned += 1
                    logger.info(f"Cleaned up file: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to clean up {dir_path}: {e}")

    return files_cleaned
