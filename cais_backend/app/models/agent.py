import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Agent(Base):
    """
    Represents an agent that can be registered and invoked by the orchestrator.
    """

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)  # 1 active, 0 inactive
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    executions = relationship(
        "AgentExecution",
        back_populates="agent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks = relationship(
        "AgentTask",
        back_populates="agent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name})>"


class AgentExecution(Base):
    """
    Records a single execution run of an agent, including its inputs,
    outputs, and status.
    """

    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(50), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    input_data = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    agent = relationship("Agent", back_populates="executions")

    __table_args__ = (
        Index("ix_agent_executions_status", "status"),
        Index("ix_agent_executions_agent_id_status", "agent_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentExecution(id={self.id}, agent_id={self.agent_id}, status={self.status})>"


class AgentTask(Base):
    """
    Represents a queued task for an agent, used by the orchestrator
    to track asynchronous work.
    """

    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name = Column(String(255), nullable=False, index=True)  # Denormalized for quick lookup
    status = Column(String(50), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    input_data = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    agent = relationship("Agent", back_populates="tasks")

    __table_args__ = (
        Index("ix_agent_tasks_status", "status"),
        Index("ix_agent_tasks_agent_name_status", "agent_name", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentTask(id={self.id}, agent_name={self.agent_name}, status={self.status})>"
