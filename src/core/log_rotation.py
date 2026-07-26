#!/usr/bin/env python3
"""
Log rotation configuration for forensic logs.
"""

import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta


class LogRotator:
    """
    Manages log rotation and archival for forensic logs.
    """

    def __init__(self, base_dir: str = "~/PROMETHEUS/logs", max_size_mb: int = 100):
        """
        Initialize the log rotator.

        Args:
            base_dir: Base directory for log files.
            max_size_mb: Maximum size of a log file before rotation (in MB).
        """
        self.base_dir = Path(base_dir).expanduser()
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def rotate_logs(self):
        """Rotate all log files if they exceed the maximum size."""
        log_dirs = ['success', 'errors', 'review_needed']

        for log_dir in log_dirs:
            log_file = self.base_dir / log_dir / f'{log_dir}.log'
            if log_file.exists() and log_file.stat().st_size > self.max_size_bytes:
                self._rotate_file(log_file)

    def _rotate_file(self, file_path: Path):
        """Rotate a single log file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rotated_path = file_path.with_suffix(f'.{timestamp}.log')

        shutil.move(str(file_path), str(rotated_path))

        # Compress the rotated file
        with open(rotated_path, 'rb') as f_in:
            with gzip.open(str(rotated_path) + '.gz', 'wb') as f_out:
                f_out.writelines(f_in)

        # Remove the uncompressed rotated file
        rotated_path.unlink()

        # Create a new empty log file
        file_path.touch()

    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove log files older than the specified number of days."""
        cutoff = datetime.now() - timedelta(days=days_to_keep)

        for log_file in self.base_dir.glob('**/*.log.gz'):
            try:
                timestamp_str = log_file.stem.split('.')[-1]
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                if timestamp < cutoff:
                    log_file.unlink()
                    print(f"Removed old log file: {log_file}")
            except (ValueError, IndexError):
                continue
