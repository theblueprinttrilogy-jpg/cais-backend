from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import synonym

from app.db.base import Base


class File(Base):
    """
    Represents a file stored in the system, with metadata and soft-delete flags.
    This model supports both drive_file_id and google_drive_file_id accessors
    for compatibility across services.
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drive_file_id = Column(String(255), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    permanently_deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Provide alias so both drive_file_id and google_drive_file_id work.
    # The property decorator allows attribute-style access.
    @property
    def google_drive_file_id(self) -> str:
        """Alias for drive_file_id to support services expecting this name."""
        return self.drive_file_id

    @google_drive_file_id.setter
    def google_drive_file_id(self, value: str) -> None:
        """Setter for google_drive_file_id that updates drive_file_id."""
        self.drive_file_id = value

    # Alternatively, we can use synonym, but property is more explicit.
    # For ORM compatibility, we also provide a synonym that can be used in queries?
    # But property works for attribute access. The janitor uses attribute access.

    def __repr__(self) -> str:
        return (
            f"<File(id={self.id}, drive_file_id={self.drive_file_id}, "
            f"is_deleted={self.is_deleted})>"
        )
