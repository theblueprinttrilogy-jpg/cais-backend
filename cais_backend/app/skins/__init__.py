"""
Skins Package - Visual Adaptation for Marketplaces

This package contains skins for visual adaptation across different marketplaces.
"""

from app.skins.base_skin import BaseSkin
from app.skins.skin_loader import SkinLoader
from app.skins.procore_skin import ProcoreSkin
from app.skins.appstore_skin import AppStoreSkin

__all__ = [
    "BaseSkin",
    "SkinLoader",
    "ProcoreSkin",
    "AppStoreSkin",
]
