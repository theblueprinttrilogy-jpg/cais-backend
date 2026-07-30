"""
Base Skin - Abstract Base Class for Marketplace Skins

This module provides the base class for all marketplace skins.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseSkin(ABC):
    """
    Abstract base class for marketplace skins.

    Each skin defines:
    - Colors (primary, secondary, background, text)
    - Fonts (family, sizes)
    - Layout (navigation, panels, spacing)
    - Components (buttons, tables, cards)
    """

    def __init__(self, platform_name: str, platform_type: str):
        """
        Initialize the skin.

        Args:
            platform_name: Name of the marketplace
            platform_type: Type of platform (web, mobile, desktop)
        """
        self.platform_name = platform_name
        self.platform_type = platform_type
        self.language = "en"
        self.style_guide = self._get_default_style_guide()

    @abstractmethod
    def _get_default_style_guide(self) -> Dict[str, Any]:
        """
        Returns the default style guide for this skin.
        Must be implemented by each subclass.
        """
        pass

    @abstractmethod
    def translate(self, language: str) -> Dict[str, Any]:
        """
        Translates the skin to the specified language.

        Args:
            language: Language code (e.g., "en", "es")

        Returns:
            dict: Translated skin configuration
        """
        pass

    @abstractmethod
    def render(self, translated_skin: Dict[str, Any]) -> str:
        """
        Renders the interface with the adapted skin.

        Args:
            translated_skin: The translated skin configuration

        Returns:
            str: Rendered HTML/interface code
        """
        pass

    def get_style_guide(self) -> Dict[str, Any]:
        """Returns the current style guide."""
        return self.style_guide

    def get_colors(self) -> Dict[str, str]:
        """Returns the color scheme."""
        return self.style_guide.get("colors", {})

    def get_fonts(self) -> Dict[str, Any]:
        """Returns the font configuration."""
        return self.style_guide.get("fonts", {})

    def get_layout(self) -> Dict[str, Any]:
        """Returns the layout configuration."""
        return self.style_guide.get("layout", {})

    def get_components(self) -> Dict[str, Any]:
        """Returns the component configuration."""
        return self.style_guide.get("components", {})

    def set_language(self, language: str):
        """Sets the current language."""
        self.language = language

    def get_marketplace_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the marketplace."""
        return {
            "platform_name": self.platform_name,
            "platform_type": self.platform_type,
            "supported_languages": ["en", "es", "fr", "de", "zh", "pt"],
            "version": "1.0"
        }

    def _get_base_colors(self) -> Dict[str, str]:
        """Base color scheme used by most skins."""
        return {
            "primary": "#2563EB",
            "secondary": "#64748B",
            "background": "#FFFFFF",
            "surface": "#F8FAFC",
            "text_primary": "#0F172A",
            "text_secondary": "#475569",
            "border": "#E2E8F0",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444"
        }
