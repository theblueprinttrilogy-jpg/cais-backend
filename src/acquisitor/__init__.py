#!/usr/bin/env python3
"""
Acquisitor Module - Document download and compression
"""

from .acquisitor import Acquisitor, DownloadResult
from .cli import main

__all__ = [
    'Acquisitor',
    'DownloadResult',
    'main'
]
