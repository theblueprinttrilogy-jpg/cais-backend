"""
Asynchronous service for WORM (Write‑Once‑Read‑Many) Ledger operations.

This service ensures that entries are inserted immutably and that
any update or delete attempt raises an exception.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WORMLedgerEntry

logger = logging.getLogger(__name__)


class ImmutableLedgerException(Exception):
    """Raised when an update or delete is attempted on the WORM Ledger."""
    pass


class WORMService:
    """
    Service for interacting with the WORM Ledger asynchronously.

    All write operations are append‑only. Updates and deletes are strictly
    forbidden.
    """

    def __init__(self, async_session_factory):
        """
        Initialise the service with an async session factory.

        Args:
            async_session_factory: A callable that returns an AsyncSession
                                   (e.g., async_sessionmaker).
        """
        self._session_factory = async_session_factory

    @staticmethod
    def _compute_hash(payload: Dict[str, Any]) -> str:
        """
        Compute a SHA‑256 hash of the payload in a deterministic manner.

        The payload is serialised to JSON with sorted keys to ensure
        reproducibility.

        Args:
            payload: Dictionary containing the fields to be hashed.

        Returns:
            Hex digest of the SHA‑256 hash.
        """
        json_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    async def add_entry(
        self,
        evidence_gcs_uri: str,
        violation_codes: Dict[str, Any],
        *,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> WORMLedgerEntry:
        """
        Insert a new immutable entry into the WORM Ledger.

        Args:
            evidence_gcs_uri: GCS URI of the evidence (e.g., plan screenshot).
            violation_codes: The matched building codes (as a dict or list).
            extra_metadata: Optional additional context to be hashed but not
                            stored directly (for audit trail).

        Returns:
            The newly created WORMLedgerEntry instance.

        Raises:
            RuntimeError: If database insertion fails.
        """
        # Build the payload that will be hashed
        payload = {
            "evidence_gcs_uri": evidence_gcs_uri,
            "violation_codes": violation_codes,
            # Include a unique nonce or timestamp to ensure uniqueness
            # (though UUID + timestamp is fine). For deterministic hashing,
            # we can include a random salt or use the UUID? But UUID is not yet generated.
            # We'll include the current UTC timestamp as ISO string.
            "timestamp": datetime.utcnow().isoformat(),
        }
        if extra_metadata:
            payload["extra"] = extra_metadata

        # Compute hash
        hash_value = self._compute_hash(payload)

        # Create the ORM object
        new_entry = WORMLedgerEntry(
            evidence_gcs_uri=evidence_gcs_uri,
            violation_codes=violation_codes,
            cryptographic_hash=hash_value,
        )

        # Insert using an async session
        async with self._session_factory() as session:
            session.add(new_entry)
            try:
                await session.commit()
                await session.refresh(new_entry)
            except Exception as e:
                await session.rollback()
                logger.exception("Failed to insert WORM entry")
                raise RuntimeError(f"Database insertion failed: {e}")

        return new_entry

    async def get_entry(self, entry_id: uuid.UUID) -> Optional[WORMLedgerEntry]:
        """
        Retrieve a single entry by its UUID.

        Args:
            entry_id: The UUID of the entry.

        Returns:
            The WORMLedgerEntry instance, or None if not found.
        """
        async with self._session_factory() as session:
            result = await session.get(WORMLedgerEntry, entry_id)
            return result

    async def get_all_entries(self, limit: int = 100, offset: int = 0) -> List[WORMLedgerEntry]:
        """
        Retrieve a paginated list of all entries (ordered by timestamp descending).

        Args:
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.

        Returns:
            List of WORMLedgerEntry instances.
        """
        from sqlalchemy import select
        stmt = select(WORMLedgerEntry).order_by(WORMLedgerEntry.timestamp.desc()).offset(offset).limit(limit)
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    # --- Forbidden operations ---

    async def update_entry(self, entry_id: uuid.UUID, **kwargs) -> None:
        """
        Update an entry – THIS IS FORBIDDEN.

        Raises:
            ImmutableLedgerException: Always.
        """
        raise ImmutableLedgerException(
            "WORM Ledger entries cannot be updated. Append‑only semantics enforced."
        )

    async def delete_entry(self, entry_id: uuid.UUID) -> None:
        """
        Delete an entry – THIS IS FORBIDDEN.

        Raises:
            ImmutableLedgerException: Always.
        """
        raise ImmutableLedgerException(
            "WORM Ledger entries cannot be deleted. Append‑only semantics enforced."
        )
