#!/usr/bin/env python3
"""
CAIS CODE COMPLIANCE Reader - Read-only integration with CAIS CODE COMPLIANCE
NO WRITE OPERATIONS - READ ONLY
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def safe_load_json(file_path: Path) -> Any:
    """Safely load JSON from a file, returning None if empty or invalid."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None


class CAISComplianceReader:
    """
    Read-only access to CAIS CODE COMPLIANCE data.
    Never modifies the original data.
    """

    def __init__(self, cais_root: str = "~/cais"):
        """
        Initialize the reader.

        Args:
            cais_root: Root directory of CAIS CODE COMPLIANCE project.
        """
        self.cais_root = Path(cais_root).expanduser()
        self.data_dir = self.cais_root / "data"
        self.audit_dir = self.cais_root / "audit"
        self.inventory_dir = self.cais_root / "inventory"

        if not self.cais_root.exists():
            raise FileNotFoundError(f"CAIS CODE COMPLIANCE not found at: {self.cais_root}")

        print(f"✅ CAIS Compliance Reader initialized")
        print(f"   Root: {self.cais_root}")

    def get_latest_forensic_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get the latest forensic snapshot data."""
        snapshots = sorted(
            self.data_dir.glob("forensics/snapshot-*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not snapshots:
            return None

        latest = snapshots[0]
        print(f"   Loading latest snapshot: {latest.name}")

        result = {
            'snapshot_path': str(latest),
            'files': {},
            'worm_chain': None,
            'logs': {},
            'metrics': {}
        }

        # Load file hashes
        hashes_file = latest / "file_hashes.json"
        hashes_data = safe_load_json(hashes_file)
        if hashes_data:
            result['files'] = hashes_data

        # Load WORM chain (safely)
        worm_chain_file = latest / "worm_forensic_chain" / "worm_chain_current.json"
        worm_data = safe_load_json(worm_chain_file)
        if worm_data:
            result['worm_chain'] = worm_data

        # Load logs
        journal_logs = latest / "system_logs" / "journal_logs.json"
        journal_data = safe_load_json(journal_logs)
        if journal_data:
            result['logs']['journal'] = journal_data

        cais_logs = latest / "system_logs" / "cais_logs.json"
        cais_data = safe_load_json(cais_logs)
        if cais_data:
            result['logs']['cais'] = cais_data

        return result

    def get_inventory(self) -> Dict[str, Any]:
        """Get the CAIS CODE COMPLIANCE inventory."""
        inventory_file = self.inventory_dir / "cais_compliance_inventory.json"

        if not inventory_file.exists():
            inventory_file = self.cais_root / "cais_compliance_inventory.json"

        data = safe_load_json(inventory_file)
        return data if data else {}

    def get_audit_data(self) -> Dict[str, Any]:
        """Get the forensic audit data."""
        audit_file = self.audit_dir / "forensic_inventory.json"
        data = safe_load_json(audit_file)
        return data if data else {}

    def get_modules(self) -> List[Dict[str, Any]]:
        """Get the list of modules from the inventory."""
        inventory = self.get_inventory()
        return inventory.get('modulos_analizados', [])

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get the overall compliance status."""
        inventory = self.get_inventory()
        return {
            'status': inventory.get('estado_general', 'unknown'),
            'completed': inventory.get('completado', []),
            'pending': inventory.get('pendientes', []),
            'compatibility': inventory.get('compatibilidad', {}),
            'dependencies': inventory.get('dependencias', {})
        }

    def get_forensic_summary(self) -> Dict[str, Any]:
        """Get a summary of forensic data."""
        snapshot = self.get_latest_forensic_snapshot()

        if not snapshot:
            return {'status': 'no_snapshot_found'}

        return {
            'status': 'available',
            'snapshot_path': snapshot.get('snapshot_path'),
            'files_count': len(snapshot.get('files', {})),
            'has_worm_chain': snapshot.get('worm_chain') is not None,
            'has_journal_logs': bool(snapshot.get('logs', {}).get('journal')),
            'has_cais_logs': bool(snapshot.get('logs', {}).get('cais'))
        }

    def get_building_codes(self) -> List[Dict[str, Any]]:
        """Get building codes from CAIS CODE COMPLIANCE."""
        codes = []
        code_files = list(self.data_dir.glob("**/*code*.json")) + \
                     list(self.data_dir.glob("**/*compliance*.json"))

        for code_file in code_files:
            data = safe_load_json(code_file)
            if data:
                if isinstance(data, dict):
                    data['_source_file'] = str(code_file)
                    codes.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item['_source_file'] = str(code_file)
                            codes.append(item)
        return codes


# Singleton instance
_reader_instance = None


def get_compliance_reader() -> CAISComplianceReader:
    """Get the singleton CAIS Compliance Reader."""
    global _reader_instance
    if _reader_instance is None:
        _reader_instance = CAISComplianceReader()
    return _reader_instance
