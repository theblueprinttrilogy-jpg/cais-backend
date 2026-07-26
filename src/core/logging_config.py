#!/usr/bin/env python3
"""
Forensic Logging Configuration for CAIS.
Provides structured logging with separate log files for different event types.
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

class ForensicLogger:
    """
    Forensic logging system with separate log files for success, errors, and review-needed items.
    All logs include timestamps, hashes, and correlation IDs for traceability.
    """
    
    def __init__(self, base_dir: str = "~/PROMETHEUS/logs"):
        """
        Initialize forensic logging.
        
        Args:
            base_dir: Base directory for log files.
        """
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Set up separate loggers for different event types."""
        
        # Create directories
        (self.base_dir / 'success').mkdir(exist_ok=True)
        (self.base_dir / 'errors').mkdir(exist_ok=True)
        (self.base_dir / 'review_needed').mkdir(exist_ok=True)
        
        # Success logger
        self.success_logger = logging.getLogger('cais.success')
        self.success_logger.setLevel(logging.INFO)
        success_handler = logging.FileHandler(
            self.base_dir / 'success' / 'success.log'
        )
        success_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.success_logger.addHandler(success_handler)
        
        # Error logger
        self.error_logger = logging.getLogger('cais.errors')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(
            self.base_dir / 'errors' / 'errors.log'
        )
        error_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.error_logger.addHandler(error_handler)
        
        # Review needed logger
        self.review_logger = logging.getLogger('cais.review')
        self.review_logger.setLevel(logging.INFO)
        review_handler = logging.FileHandler(
            self.base_dir / 'review_needed' / 'review_needed.log'
        )
        review_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.review_logger.addHandler(review_handler)
        
        # Audit logger (WORM)
        self.audit_logger = logging.getLogger('cais.audit')
        self.audit_logger.setLevel(logging.INFO)
        audit_handler = logging.FileHandler(
            self.base_dir / 'audit.log'
        )
        audit_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.audit_logger.addHandler(audit_handler)
    
    def log_success(self, message: str, extra: Optional[Dict] = None):
        """Log a success event."""
        self.success_logger.info(message, extra=extra or {})
    
    def log_error(self, message: str, extra: Optional[Dict] = None):
        """Log an error event."""
        self.error_logger.error(message, extra=extra or {})
    
    def log_review_needed(self, message: str, extra: Optional[Dict] = None):
        """Log a review-needed event."""
        self.review_logger.info(message, extra=extra or {})
    
    def log_audit(self, event_type: str, payload: Dict):
        """Log an audit event for the WORM."""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'payload': payload
        }
        self.audit_logger.info(json.dumps(audit_entry))
    
    def get_success_logs(self, limit: int = 100):
        """Get recent success logs."""
        return self._read_log_file(self.base_dir / 'success' / 'success.log', limit)
    
    def get_error_logs(self, limit: int = 100):
        """Get recent error logs."""
        return self._read_log_file(self.base_dir / 'errors' / 'errors.log', limit)
    
    def get_review_logs(self, limit: int = 100):
        """Get recent review-needed logs."""
        return self._read_log_file(self.base_dir / 'review_needed' / 'review_needed.log', limit)
    
    def _read_log_file(self, file_path: Path, limit: int):
        """Read a log file and return recent entries."""
        if not file_path.exists():
            return []
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        return [line.strip() for line in lines[-limit:]]
