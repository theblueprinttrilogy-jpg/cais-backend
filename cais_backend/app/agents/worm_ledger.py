"""
WORM Ledger Agent - Immutable Forensic Evidence Recording

This agent implements a Write Once, Read Many (WORM) ledger for
forensic evidence. Each violation is recorded with a cryptographic
hash, timestamp, and immutable reference.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 4.5
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session
from app.db.models import WORMLedgerEntry

logger = logging.getLogger(__name__)


class WormLedger:
    """
    WORM Ledger Agent - Immutable Forensics Recorder

    Responsibilities:
    1. Record each detected violation with immutable timestamp
    2. Generate cryptographic SHA-256 hash of the violation data
    3. Store evidence reference (GCS URI or local path)
    4. Ensure append-only semantics (no updates or deletions)
    5. Provide audit trail for forensic purposes
    6. Verify integrity of any entry
    """

    def __init__(self, db_session: Session):
        """
        Initialize the WORM Ledger with a database session.

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db = db_session
        self.ledger_name = "CAIS_FORENSIC_LEDGER"

    def record_violation(
        self,
        document_id: str,
        violation_id: str,
        violation_data: Dict[str, Any],
        jurisdiction: str,
        evidence_uri: Optional[str] = None
    ) -> WORMLedgerEntry:
        """
        Record a violation in the WORM ledger.

        Args:
            document_id: UUID of the document (as string)
            violation_id: UUID of the violation (as string)
            violation_data: Dict with violation details (type, severity, description, etc.)
            jurisdiction: Jurisdiction where violation was detected
            evidence_uri: GCS URI or local path to evidence image (optional)

        Returns:
            WORMLedgerEntry: The created ledger entry
        """
        # Prepare the payload for hashing (excluding timestamp to avoid non‑determinism)
        payload = {
            "document_id": str(document_id),
            "violation_id": str(violation_id),
            "violation_data": violation_data,
            "jurisdiction": jurisdiction,
            "ledger": self.ledger_name,
        }

        # Generate SHA-256 hash
        payload_str = json.dumps(payload, sort_keys=True)
        cryptographic_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

        # If no evidence URI provided, use a placeholder
        if not evidence_uri:
            evidence_uri = f"local://evidence/{violation_id}.png"

        # Create ledger entry
        entry = WORMLedgerEntry(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            evidence_gcs_uri=evidence_uri,
            violation_codes={
                "violation_id": str(violation_id),
                "document_id": str(document_id),
                "jurisdiction": jurisdiction,
                "violation_type": violation_data.get("type", "unknown"),
                "severity": violation_data.get("severity", "warning"),
                "description": violation_data.get("description", ""),
                "code_reference": violation_data.get("code_reference", ""),
                "page_num": violation_data.get("page_num"),
                "evidence_path": evidence_uri
            },
            cryptographic_hash=cryptographic_hash
        )

        # Save to database (append‑only)
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        logger.info(
            f"WORM Ledger: Recorded violation {violation_id} "
            f"with hash {cryptographic_hash[:8]}..."
        )

        return entry

    def record_action(
        self,
        action: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> WORMLedgerEntry:
        """
        Record any system action (e.g., kill_switch, self‑healing) in the WORM ledger.

        Args:
            action: Action name (e.g., 'kill_switch_activated')
            data: Data associated with the action
            user_id: Optional user ID

        Returns:
            WORMLedgerEntry: The created ledger entry
        """
        payload = {
            "action": action,
            "data": data,
            "user_id": user_id,
            "ledger": self.ledger_name,
        }

        payload_str = json.dumps(payload, sort_keys=True)
        cryptographic_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

        entry = WORMLedgerEntry(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            evidence_gcs_uri=f"action:{action}",
            violation_codes={"action": action, "data": data, "user_id": user_id},
            cryptographic_hash=cryptographic_hash
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        logger.info(f"WORM Ledger: Action '{action}' recorded with hash {cryptographic_hash[:8]}...")
        return entry

    def record_multiple_violations(
        self,
        violations: List[Dict[str, Any]],
        document_id: str,
        jurisdiction: str
    ) -> List[WORMLedgerEntry]:
        """
        Record multiple violations in a single batch.

        Args:
            violations: List of violation dicts (each must have 'id')
            document_id: UUID of the document
            jurisdiction: Jurisdiction

        Returns:
            List[WORMLedgerEntry]: The created ledger entries
        """
        entries = []
        for v in violations:
            entry = self.record_violation(
                document_id=document_id,
                violation_id=v.get("id", str(uuid4())),
                violation_data=v,
                jurisdiction=jurisdiction,
                evidence_uri=v.get("evidence_path")
            )
            entries.append(entry)
        return entries

    def get_entry_by_hash(self, hash_value: str) -> Optional[WORMLedgerEntry]:
        """
        Retrieve a ledger entry by its cryptographic hash.

        Args:
            hash_value: SHA-256 hash (hex string)

        Returns:
            WORMLedgerEntry or None
        """
        return self.db.query(WORMLedgerEntry).filter(
            WORMLedgerEntry.cryptographic_hash == hash_value
        ).first()

    def get_entries_by_document(self, document_id: str) -> List[WORMLedgerEntry]:
        """
        Get all ledger entries for a document.

        Args:
            document_id: UUID of the document (as string)

        Returns:
            List[WORMLedgerEntry]: List of entries
        """
        # Since violation_codes is JSONB, we can filter using containment
        # This is a simple approach; for production, consider using JSONB operators
        entries = self.db.query(WORMLedgerEntry).filter(
            WORMLedgerEntry.violation_codes['document_id'].astext == str(document_id)
        ).all()
        return entries

    def get_entries_by_jurisdiction(self, jurisdiction: str) -> List[WORMLedgerEntry]:
        """
        Get all ledger entries for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction code

        Returns:
            List[WORMLedgerEntry]: List of entries
        """
        return self.db.query(WORMLedgerEntry).filter(
            WORMLedgerEntry.violation_codes['jurisdiction'].astext == jurisdiction
        ).all()

    def get_audit_trail(self, limit: int = 100) -> List[WORMLedgerEntry]:
        """
        Get the most recent entries (audit trail).

        Args:
            limit: Maximum number of entries

        Returns:
            List[WORMLedgerEntry]: List of entries, newest first
        """
        return self.db.query(WORMLedgerEntry).order_by(
            WORMLedgerEntry.timestamp.desc()
        ).limit(limit).all()

    def verify_entry(self, entry: WORMLedgerEntry) -> bool:
        """
        Verify the integrity of a ledger entry by recomputing its hash.

        Args:
            entry: WORMLedgerEntry object

        Returns:
            bool: True if hash matches, False otherwise
        """
        # Reconstruct the payload from the entry data
        # Determine if it's a violation entry or action entry
        if "violation_id" in entry.violation_codes:
            payload = {
                "document_id": entry.violation_codes.get("document_id"),
                "violation_id": entry.violation_codes.get("violation_id"),
                "violation_data": {
                    "type": entry.violation_codes.get("violation_type"),
                    "severity": entry.violation_codes.get("severity"),
                    "description": entry.violation_codes.get("description"),
                    "code_reference": entry.violation_codes.get("code_reference"),
                    "page_num": entry.violation_codes.get("page_num"),
                    "evidence_path": entry.violation_codes.get("evidence_path"),
                },
                "jurisdiction": entry.violation_codes.get("jurisdiction"),
                "ledger": self.ledger_name,
            }
        else:
            # Action entry
            payload = {
                "action": entry.violation_codes.get("action"),
                "data": entry.violation_codes.get("data"),
                "user_id": entry.violation_codes.get("user_id"),
                "ledger": self.ledger_name,
            }

        payload_str = json.dumps(payload, sort_keys=True)
        computed_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

        is_valid = computed_hash == entry.cryptographic_hash
        if not is_valid:
            logger.warning(f"Integrity check failed for entry {entry.id}")
        return is_valid

    def verify_all_entries(self) -> Dict[str, Any]:
        """
        Verify integrity of all entries in the ledger.

        Returns:
            Dict: Summary with total, valid, invalid counts
        """
        entries = self.db.query(WORMLedgerEntry).all()
        total = len(entries)
        valid = 0
        invalid = 0

        for entry in entries:
            if self.verify_entry(entry):
                valid += 1
            else:
                invalid += 1

        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "integrity": "OK" if invalid == 0 else "COMPROMISED"
        }
