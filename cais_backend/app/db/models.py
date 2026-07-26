"""
SQLAlchemy declarative models for the CAIS backend.

All tables are defined here. The WORM Ledger is append‑only.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


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
        doc="Unique identifier for the ledger entry.",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Forensic timestamp of the recording (UTC).",
    )
    evidence_gcs_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="GCS URI of the immutable visual evidence (plan screenshot, etc.).",
    )
    violation_codes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Structured list or object of building codes matched (JSONB).",
    )
    cryptographic_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA‑256 hash of the serialised payload (excluding timestamp).",
    )

    # Optional: add a comment to the table to indicate append‑only
    __table_args__ = (
        # This is a comment only; enforcement is in application logic.
        {
            "comment": "Append‑only ledger – updates and deletes are forbidden."
        },
    )
