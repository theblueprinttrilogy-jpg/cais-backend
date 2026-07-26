#!/usr/bin/env python3
"""
WORM Ledger - Write Once Read Many immutable ledger for forensic traceability.
"""

import os
import json
import hashlib
import hmac
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class WORMEntry:
    """A single entry in the WORM ledger."""
    sequence: int
    timestamp: str
    event_type: str
    payload: Dict[str, Any]
    actor: str
    previous_hash: str
    hash: str = ""
    signature: str = ""
    node_id: str = "local"
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the entry."""
        data = {
            'sequence': self.sequence,
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'payload': self.payload,
            'previous_hash': self.previous_hash,
            'actor': self.actor,
            'node_id': self.node_id
        }
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def sign(self, secret_key: bytes) -> str:
        """Sign the entry using HMAC-SHA256."""
        data = {
            'sequence': self.sequence,
            'hash': self.hash,
            'timestamp': self.timestamp,
            'event_type': self.event_type
        }
        content = json.dumps(data, sort_keys=True, default=str).encode()
        return hmac.new(secret_key, content, hashlib.sha256).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'sequence': self.sequence,
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'payload': self.payload,
            'actor': self.actor,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'signature': self.signature,
            'node_id': self.node_id
        }


class WormLedger:
    """
    WORM (Write Once Read Many) ledger for immutable record-keeping.
    Implements SHA-256 chaining for integrity verification.
    """
    
    GENESIS_HASH = "0" * 64
    
    def __init__(self, storage_path: str = "~/PROMETHEUS/data/worm"):
        """
        Initialize the WORM ledger.
        
        Args:
            storage_path: Path to store the ledger.
        """
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.ledger_file = self.storage_path / 'worm_ledger.jsonl'
        self.secret_key = os.getenv('WORM_SECRET_KEY', 'default-secret-key-change-me').encode()
        
        self._sequence = 0
        self._last_hash = self.GENESIS_HASH
        self._entries: List[WORMEntry] = []
        self._loaded = False
        
        self._load_ledger()
    
    def _load_ledger(self):
        """Load existing ledger entries."""
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            entry = WORMEntry(
                                sequence=data['sequence'],
                                timestamp=data['timestamp'],
                                event_type=data['event_type'],
                                payload=data['payload'],
                                actor=data['actor'],
                                previous_hash=data['previous_hash'],
                                hash=data['hash'],
                                signature=data.get('signature', ''),
                                node_id=data.get('node_id', 'local')
                            )
                            self._entries.append(entry)
                            self._sequence = max(self._sequence, entry.sequence)
                            self._last_hash = entry.hash
                        except json.JSONDecodeError:
                            continue
                self._loaded = True
            except Exception as e:
                print(f"⚠️ Error loading WORM ledger: {e}")
        
        self._sequence += 1
    
    def append_entry(self, event_type: str, data: Dict[str, Any], actor: str = "system") -> Tuple[bool, Optional[WORMEntry]]:
        """
        Append a new entry to the ledger.
        
        Args:
            event_type: Type of event.
            data: Event data.
            actor: User or system performing the action.
            
        Returns:
            Tuple of (success, entry).
        """
        try:
            entry = WORMEntry(
                sequence=self._sequence,
                timestamp=datetime.now().isoformat(),
                event_type=event_type,
                payload=data,
                actor=actor,
                previous_hash=self._last_hash
            )
            
            # Calculate hash
            entry.hash = entry.calculate_hash()
            
            # Sign the entry
            entry.signature = entry.sign(self.secret_key)
            
            # Write to file
            with open(self.ledger_file, 'a') as f:
                f.write(json.dumps(entry.to_dict(), default=str) + '\n')
                f.flush()
            
            # Update state
            self._entries.append(entry)
            self._sequence += 1
            self._last_hash = entry.hash
            
            return True, entry
            
        except Exception as e:
            print(f"❌ Failed to append to WORM ledger: {e}")
            return False, None
    
    def get_entries(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get entries from the ledger.
        
        Args:
            event_type: Filter by event type.
            limit: Maximum number of entries to return.
            
        Returns:
            List of entries as dictionaries.
        """
        entries = self._entries[-limit:] if limit else self._entries
        
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        
        return [e.to_dict() for e in entries]
    
    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the entire ledger.
        
        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []
        previous_hash = self.GENESIS_HASH
        
        for i, entry in enumerate(self._entries):
            # Check hash
            computed_hash = entry.calculate_hash()
            if computed_hash != entry.hash:
                errors.append(f"Hash mismatch at sequence {entry.sequence}")
            
            # Check chain
            if entry.previous_hash != previous_hash:
                errors.append(f"Chain break at sequence {entry.sequence}")
            
            # Check signature
            computed_signature = entry.sign(self.secret_key)
            if computed_signature != entry.signature:
                errors.append(f"Signature mismatch at sequence {entry.sequence}")
            
            previous_hash = entry.hash
        
        return len(errors) == 0, errors
    
    def get_status(self) -> Dict[str, Any]:
        """Get ledger status."""
        integrity, errors = self.verify_integrity()
        return {
            'total_entries': len(self._entries),
            'last_block': self._last_hash[:16] + '...' if self._last_hash else 'None',
            'last_hash': self._last_hash[:16] + '...' if self._last_hash else 'None',
            'integrity': integrity,
            'integrity_errors': errors,
            'errors_count': len(errors)
        }
    
    def get_chain_hashes(self) -> List[str]:
        """Get all hashes in the chain for verification."""
        return [entry.hash for entry in self._entries]
