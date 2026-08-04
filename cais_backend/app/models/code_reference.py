from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class CodeReference(Base):
    """
    SQLAlchemy model for building code references with vector embeddings.

    This table stores code sections, their textual descriptions, and a
    384-dimensional embedding vector for semantic similarity search.
    """

    __tablename__ = "code_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    code_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(384), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return (
            f"<CodeReference(id={self.id}, section='{self.section}', "
            f"jurisdiction='{self.jurisdiction}', code_type='{self.code_type}')>"
        )
