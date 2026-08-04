import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Union

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.db.session import async_session_factory
from app.models.agent import Agent, AgentExecution, AgentTask
from app.models.file import File
from app.services.drive import GoogleDriveService
from app.services.janitor import JanitorService

logger = logging.getLogger(__name__)

# Export required symbols
SessionLocal = async_session_factory


@dataclass
class CodeReference:
    """
    Dataclass representing a building code reference.
    Used by agents that need to cite specific codes and sections.
    """
    code: str
    section: str
    text: str


T = TypeVar("T", bound=BaseAgent)


class Orchestrator:
    """
    Central orchestrator for dispatching tasks to agents, managing their lifecycle,
    and persisting state to the database using asynchronous SQLAlchemy.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        drive_service: GoogleDriveService,
        agent_registry: Dict[str, T],
    ) -> None:
        """
        Initialize the orchestrator with an async database session and services.

        :param db_session: Async SQLAlchemy session for all database operations.
        :param drive_service: Service for Google Drive interactions.
        :param agent_registry: Mapping of agent names to agent instances.
        """
        self.db_session = db_session
        self.drive_service = drive_service
        self.agent_registry = agent_registry
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self) -> None:
        """
        Perform any asynchronous initialization needed, such as verifying
        agent availability or loading configuration. This method ensures
        the orchestrator is ready to accept tasks without mixing sync/async.
        """
        logger.info("Initializing orchestrator")
        # Check database connectivity by running a simple query
        try:
            stmt = select(Agent).limit(1)
            await self.db_session.execute(stmt)
            logger.info("Database connection verified")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise RuntimeError("Orchestrator initialization failed") from e

        # Initialize each agent if they have async setup
        for name, agent in self.agent_registry.items():
            if hasattr(agent, "initialize") and asyncio.iscoroutinefunction(
                agent.initialize
            ):
                await agent.initialize()
            logger.info(f"Agent '{name}' initialized")

    async def _get_or_create_agent(self, agent_name: str) -> Agent:
        """
        Retrieve an Agent by name from the database, or create one if missing.

        :param agent_name: Name of the agent.
        :return: Agent instance.
        """
        stmt = select(Agent).where(Agent.name == agent_name)
        result = await self.db_session.execute(stmt)
        agent = result.scalar_one_or_none()

        if agent is None:
            logger.info(f"Agent '{agent_name}' not found in DB, creating...")
            agent = Agent(
                name=agent_name,
                description=f"Auto-created agent for '{agent_name}'",
                is_active=1,
            )
            self.db_session.add(agent)
            await self.db_session.commit()
            await self.db_session.refresh(agent)
            logger.info(f"Agent '{agent_name}' created with ID {agent.id}")

        return agent

    async def execute_task(
        self,
        task_id: str,
        agent_name: str,
        input_data: Dict[str, Any],
        priority: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute a task using the specified agent.

        Before creating the task record, it ensures that an Agent record
        exists in the database for the given agent_name (auto-creates if missing).

        :param task_id: Unique identifier for the task.
        :param agent_name: Name of the agent to use.
        :param input_data: Input parameters for the agent.
        :param priority: Task priority (higher = more urgent).
        :return: Result dictionary from the agent.
        :raises ValueError: If agent not found in registry or task already running.
        """
        if agent_name not in self.agent_registry:
            raise ValueError(f"Agent '{agent_name}' not registered")

        agent_instance = self.agent_registry[agent_name]

        # Check if task already exists and is running
        existing = await self._get_task(task_id)
        if existing and existing.status == "running":
            raise ValueError(f"Task {task_id} is already running")

        # Ensure Agent record exists in the database and get its ID
        agent_record = await self._get_or_create_agent(agent_name)
        agent_id = agent_record.id

        # Create task record with the resolved agent_id
        task_record = AgentTask(
            id=task_id,
            agent_id=agent_id,
            agent_name=agent_name,
            status="pending",
            priority=priority,
            input_data=input_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db_session.add(task_record)
        await self.db_session.commit()
        await self.db_session.refresh(task_record)

        # Start execution in a background task to avoid blocking
        execution_task = asyncio.create_task(
            self._run_agent(agent_instance, task_record, input_data)
        )
        self._running_tasks[task_id] = execution_task

        # Return immediately; caller can poll status
        return {"task_id": task_id, "status": "started"}

    async def _run_agent(
        self, agent: BaseAgent, task: AgentTask, input_data: Dict[str, Any]
    ) -> None:
        """
        Internal method that runs the agent and updates the task record.

        :param agent: Agent instance.
        :param task: Task record.
        :param input_data: Input data.
        """
        try:
            # Update status to running
            await self._update_task_status(task.id, "running")
            # Execute the agent (assume it's async)
            result = await agent.execute(input_data)
            # Update task with result
            await self._update_task_status(task.id, "completed", result=result)
            logger.info(f"Task {task.id} completed successfully")
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            await self._update_task_status(task.id, "failed", error=str(e))
        finally:
            # Remove from running tasks
            self._running_tasks.pop(task.id, None)

    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update the status and result of a task in the database.

        :param task_id: Task identifier.
        :param status: New status string.
        :param result: Optional result dictionary.
        :param error: Optional error message.
        """
        values = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if result is not None:
            values["result"] = result
        if error is not None:
            values["error"] = error
        stmt = update(AgentTask).where(AgentTask.id == task_id).values(**values)
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def _get_task(self, task_id: str) -> Optional[AgentTask]:
        """
        Retrieve a task record by ID.

        :param task_id: Task identifier.
        :return: AgentTask instance or None.
        """
        stmt = select(AgentTask).where(AgentTask.id == task_id)
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status and result of a task.

        :param task_id: Task identifier.
        :return: Dictionary with status, result, and error fields.
        :raises ValueError: If task not found.
        """
        task = await self._get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return {
            "id": task.id,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }

    async def cancel_task(self, task_id: str) -> bool:
        """
        Attempt to cancel a running task.

        :param task_id: Task identifier.
        :return: True if cancellation was attempted, False if task not running.
        """
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} cancelled")
                await self._update_task_status(task_id, "cancelled")
                return True
        return False

    async def run_janitor_cleanup(self, aggressive: bool = False) -> Dict[str, Any]:
        """
        Run the janitor cleanup using the JanitorService, with disk-space awareness.

        :param aggressive: If True, force aggressive cleanup regardless of disk state.
        :return: Metrics dictionary from the janitor.
        """
        janitor = JanitorService(self.db_session, self.drive_service)
        return await janitor.run_cleanup(aggressive=aggressive)

    async def shutdown(self) -> None:
        """
        Gracefully shut down the orchestrator, cancelling any running tasks.
        """
        logger.info("Shutting down orchestrator")
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task {task_id}")
        # Wait for all tasks to finish cancellation
        if self._running_tasks:
            await asyncio.gather(
                *self._running_tasks.values(), return_exceptions=True
            )
        self._running_tasks.clear()
        # Shutdown each agent if they have a shutdown method
        for name, agent in self.agent_registry.items():
            if hasattr(agent, "shutdown") and asyncio.iscoroutinefunction(
                agent.shutdown
            ):
                await agent.shutdown()
        logger.info("Orchestrator shut down")


# Alias for compatibility with ingestion_worker and other consumers
AutonomousOrchestrator = Orchestrator
