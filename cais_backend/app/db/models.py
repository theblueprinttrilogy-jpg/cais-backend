"""
SQLAlchemy declarative models for the CAIS backend.

All tables are defined here. The WORM Ledger is append‑only.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, String, Integer, Float, Boolean, Text, ForeignKey,
    Index, JSON, Enum, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============================================================
# USER MODEL
# ============================================================

class User(Base):
    """User account model."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    trial_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)

    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    preferred_timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")


# ============================================================
# PROJECT MODEL
# ============================================================

class Project(Base):
    """Project model."""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_projects_user_id", "user_id"),
        Index("idx_projects_status", "status"),
    )


# ============================================================
# DOCUMENT MODEL
# ============================================================

class Document(Base):
    """Document model for uploaded files."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="documents")
    violations = relationship("Violation", back_populates="document", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="document", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        Index("idx_documents_project_id", "project_id"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_language", "language"),
    )


# ============================================================
# VIOLATION MODEL
# ============================================================

class Violation(Base):
    """Violation model for detected code violations."""
    __tablename__ = "violations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    violation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="warning")
    description: Mapped[str] = mapped_column(Text, nullable=False)

    code_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    coordinates: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    evidence_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    page_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="detected", nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="violations")

    __table_args__ = (
        Index("idx_violations_document_id", "document_id"),
        Index("idx_violations_severity", "severity"),
        Index("idx_violations_status", "status"),
    )


# ============================================================
# CODE REFERENCE MODEL
# ============================================================

class CodeReference(Base):
    """Code reference model for building codes."""
    __tablename__ = "code_references"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    code_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)

    # pgvector embedding (for semantic search)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_codes_code_type", "code_type"),
        Index("idx_codes_jurisdiction", "jurisdiction"),
        Index("idx_codes_section", "section"),
    )


# ============================================================
# REPORT MODEL
# ============================================================

class Report(Base):
    """Report model for Forensic Facts Dossier."""
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="report")


# ============================================================
# PAYMENT MODEL
# ============================================================

class Payment(Base):
    """Payment model for subscription payments."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="stripe", nullable=False)

    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="payments")

    __table_args__ = (
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_status", "status"),
    )


# ============================================================
# WORM LEDGER MODEL (IMMUTABLE)
# ============================================================

class WORMLedgerEntry(Base):
    """
    Immutable, append‑only ledger for forensic evidence records.

    Once inserted, rows must never be updated or deleted.
    """
    __tablename__ = "worm_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique identifier for the ledger entry."
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Forensic timestamp of the recording (UTC)."
    )
    evidence_gcs_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="GCS URI of the immutable visual evidence."
    )
    violation_codes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Structured list or object of building codes matched (JSONB)."
    )
    cryptographic_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA‑256 hash of the serialised payload (excluding timestamp)."
    )

    __table_args__ = (
        Index("idx_worm_timestamp", "timestamp"),
        {"comment": "Append‑only ledger – updates and deletes are forbidden."}
    )
