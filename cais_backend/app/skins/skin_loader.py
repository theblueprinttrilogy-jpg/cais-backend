"""
Skin Loader - Loads and Caches Marketplace Skins

This module handles the loading of skins for all marketplaces.
"""

import logging
from typing import Optional, Dict, Any

from app.skins.base_skin import BaseSkin
from app.skins.procore_skin import ProcoreSkin
from app.skins.appstore_skin import AppStoreSkin

logger = logging.getLogger(__name__)


class SkinLoader:
    """
    Loads and caches marketplace skins.

    Supports all 21 marketplaces with lazy loading.
    """

    SKIN_MAP = {
        "procore": ProcoreSkin,
        "autodesk_forma": "app.skins.autodesk_skin.AutodeskSkin",
        "oracle_aconex": "app.skins.aconex_skin.AconexSkin",
        "bentley_itwin": "app.skins.bentley_skin.BentleySkin",
        "plangrid": "app.skins.plangrid_skin.PlanGridSkin",
        "fieldwire": "app.skins.fieldwire_skin.FieldwireSkin",
        "buildertrend": "app.skins.buildertrend_skin.BuildertrendSkin",
        "newforma": "app.skins.newforma_skin.NewformaSkin",
        "sharepoint": "app.skins.sharepoint_skin.SharePointSkin",
        "dropbox": "app.skins.dropbox_skin.DropboxSkin",
        "google_workspace": "app.skins.google_workspace_skin.GoogleWorkspaceSkin",
        "servicetitan": "app.skins.servicetitan_skin.ServiceTitanSkin",
        "simpro": "app.skins.simpro_skin.SimproSkin",
        "esri_arcgis": "app.skins.esri_skin.EsriSkin",
        "cityworks": "app.skins.cityworks_skin.CityworksSkin",
        "revit": "app.skins.revit_skin.RevitSkin",
        "autocad": "app.skins.autocad_skin.AutoCadSkin",
        "bluebeam_revu": "app.skins.bluebeam_skin.BluebeamSkin",
        "accela": "app.skins.accela_skin.AccelaSkin",
        "appstore": AppStoreSkin,
        "googleplay": "app.skins.googleplay_skin.GooglePlaySkin",
    }

    def __init__(self):
        self._skin_cache = {}
        self._style_guide_cache = {}

    def load_skin(self, platform: str) -> BaseSkin:
        """
        Loads and returns the skin for the specified platform.

        Args:
            platform: The marketplace identifier

        Returns:
            BaseSkin: The loaded skin instance
        """
        platform = platform.lower()

        if platform in self._skin_cache:
            return self._skin_cache[platform]

        skin_class = self.SKIN_MAP.get(platform)
        if skin_class is None:
            logger.warning(f"No skin found for '{platform}', using default ProcoreSkin")
            skin_class = ProcoreSkin

        if isinstance(skin_class, str):
            import importlib
            module_path, class_name = skin_class.rsplit(".", 1)
            module = importlib.import_module(module_path)
            skin_class = getattr(module, class_name)

        skin = skin_class()
        self._skin_cache[platform] = skin

        logger.info(f"Loaded skin for platform: {platform}")
        return skin

    def get_style_guide(self, platform: str) -> Dict[str, Any]:
        """Returns the style guide for a specific platform."""
        platform = platform.lower()

        if platform in self._style_guide_cache:
            return self._style_guide_cache[platform]

        skin = self.load_skin(platform)
        style_guide = skin.get_style_guide()
        self._style_guide_cache[platform] = style_guide

        return style_guide

    def get_platform_colors(self, platform: str) -> Dict[str, str]:
        """Returns the color scheme for a specific platform."""
        style_guide = self.get_style_guide(platform)
        return style_guide.get("colors", {})

    def clear_cache(self):
        """Clears all cached skins and style guides."""
        self._skin_cache.clear()
        self._style_guide_cache.clear()
        logger.info("Cleared all skin caches")

    def list_available_skins(self) -> list:
        """Returns a list of all available skins."""
        return list(self.SKIN_MAP.keys())
