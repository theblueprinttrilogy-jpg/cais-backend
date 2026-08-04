"""
app/services/worker.py

Standalone asynchronous forensic task worker.
Polls the database for pending/processing AgentTask records,
executes forensic artifact processing (simulated ingestion),
generates structured violation results, and updates task status.

Designed to run as a background service.
"""

import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.agent import AgentTask

logger = logging.getLogger(__name__)

# Severity categories and their weights/costs (aligned with endpoints.py)
SEVERITY_LIST = ["critical", "high", "medium", "low"]
DEFAULT_SEVERITY = "low"


def simulate_forensic_analysis(file_path: str) -> Dict[str, Any]:
    """
    Simulate forensic artifact processing on a given file.
    Returns a dictionary containing detected violations and summary stats.

    In production, this would call real OCR, plan inspection, code matching, etc.
    For now, we generate synthetic violation data based on the file name/path.
    """
    # Random seed based on file path for deterministic simulation
    seed = hash(file_path) & 0xFFFFFFFF
    random.seed(seed)

    # Decide number of violations (1 to 5)
    num_violations = random.randint(1, 5)

    violations = []
    for _ in range(num_violations):
        severity = random.choice(SEVERITY_LIST)
        violations.append({
            "section": f"SIM-{random.randint(100, 999)}",
            "title": f"Simulated violation ({severity})",
            "description": f"This is a simulated {severity} severity violation detected in {os.path.basename(file_path)}.",
            "severity": severity,
        })

    # Summary
    severity_counts = {sev: 0 for sev in SEVERITY_LIST}
    for v in violations:
        severity_counts[v["severity"]] += 1

    summary = {
        "total_violations": len(violations),
        "severity_counts": severity_counts,
    }

    return {
        "violations": violations,
        "summary": summary,
    }


async def process_task(task: AgentTask, session: AsyncSession) -> None:
    """
    Process a single AgentTask: simulate forensic analysis, update task status and result.
    """
    # Extract file path from input_data
    input_data = task.input_data or {}
    file_path = input_data.get("file_path")

    if not file_path:
        # If no file path, we cannot process; mark as failed with error
        task.status = "failed"
        task.error = "No file_path provided in input_data"
        task.updated_at = datetime.utcnow()
        await session.commit()
        logger.warning(f"Task {task.id} has no file_path, marked as failed.")
        return

    if not os.path.exists(file_path):
        # File not found; mark as failed
        task.status = "failed"
        task.error = f"File not found: {file_path}"
        task.updated_at = datetime.utcnow()
        await session.commit()
        logger.warning(f"Task {task.id} file not found: {file_path}")
        return

    try:
        # Simulate forensic analysis (blocking I/O - run in thread to avoid blocking event loop)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, simulate_forensic_analysis, file_path)

        # Mark task as completed with results
        task.status = "completed"
        task.result = result
        task.error = None
        task.updated_at = datetime.utcnow()
        await session.commit()
        logger.info(f"Task {task.id} processed successfully: {len(result['violations'])} violations found.")

    except Exception as e:
        # Catch any exception during processing
        task.status = "failed"
        task.error = str(e)
        task.updated_at = datetime.utcnow()
        await session.commit()
        logger.error(f"Task {task.id} failed with error: {e}", exc_info=True)


async def worker_loop() -> None:
    """
    Main worker loop: polls database every 2 seconds for tasks with status 'pending' or 'processing',
    processes them sequentially.
    """
    logger.info("Forensic worker started, polling every 2 seconds.")

    while True:
        try:
            async with async_session_factory() as session:
                # Fetch tasks with status 'pending' or 'processing'
                stmt = select(AgentTask).where(
                    AgentTask.status.in_(["pending", "processing"])
                ).order_by(AgentTask.created_at).limit(10)  # Process up to 10 per cycle
                result = await session.execute(stmt)
                tasks = result.scalars().all()

                if tasks:
                    logger.info(f"Found {len(tasks)} tasks to process.")
                    for task in tasks:
                        # If task is 'pending', set to 'processing' first
                        if task.status == "pending":
                            task.status = "processing"
                            task.updated_at = datetime.utcnow()
                            await session.commit()
                            logger.debug(f"Task {task.id} set to processing.")

                        # Now process the task
                        await process_task(task, session)

                # Sleep before next poll
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.info("Worker loop cancelled, shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
            # Sleep a bit before retrying to avoid tight loop on persistent errors
            await asyncio.sleep(2)


async def run_forensic_worker() -> None:
    """
    Entry point for the forensic worker. Runs the worker loop with proper logging.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        await worker_loop()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
    except Exception as e:
        logger.critical(f"Fatal error in worker: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run_forensic_worker())
