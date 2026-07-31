"""
Autodesk Skin - Modern Style with Visual Maps and 3D

Autodesk Forma has a modern, polished, very visual interface with predominant white
and side panels framing maps, volumes, and analysis.
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class AutodeskSkin(BaseSkin):
    """
    Autodesk Forma marketplace skin.

    Style: Modern, visual, maps 3D
    Type: Web-based design and analysis
    """

    def __init__(self):
        super().__init__("Autodesk Forma", "web")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#1A73E8",
                "secondary": "#34A853",
                "background": "#FFFFFF",
                "surface": "#F8F9FA",
                "text_primary": "#202124",
                "text_secondary": "#5F6368",
                "border": "#DADCE0",
                "success": "#34A853",
                "warning": "#FBBC04",
                "error": "#EA4335",
                "navbar": "#FFFFFF",
                "panel": "#F8F9FA",
                "card_shadow": "0 2px 12px rgba(0,0,0,0.08)"
            },
            "fonts": {
                "family": "Google Sans, -apple-system, BlinkMacSystemFont, sans-serif",
                "heading": "Google Sans, sans-serif",
                "body": "Roboto, sans-serif",
                "mono": "JetBrains Mono, monospace",
                "sizes": {
                    "xs": "0.75rem",
                    "sm": "0.875rem",
                    "base": "1rem",
                    "lg": "1.125rem",
                    "xl": "1.25rem",
                    "2xl": "1.5rem",
                    "3xl": "1.875rem"
                }
            },
            "layout": {
                "max_width": "100%",
                "sidebar_width": "320px",
                "navbar_height": "64px",
                "spacing": "1.5rem",
                "border_radius": "12px"
            },
            "components": {
                "button": {
                    "padding": "0.5rem 1.5rem",
                    "border_radius": "8px",
                    "font_weight": "500"
                },
                "card": {
                    "padding": "1.5rem",
                    "border_radius": "12px",
                    "shadow": "0 2px 12px rgba(0,0,0,0.08)"
                },
                "panel": {
                    "background": "#F8F9FA",
                    "border_radius": "12px",
                    "padding": "1.5rem"
                }
            }
        }

    def translate(self, language: str) -> Dict[str, Any]:
        """Translate the skin to the specified language."""
        self.language = language
        return self.style_guide

    def render(self, translated_skin: Dict[str, Any]) -> str:
        """Render the interface with the adapted skin."""
        colors = translated_skin.get("colors", {})
        fonts = translated_skin.get("fonts", {})
        layout = translated_skin.get("layout", {})

        return f"""
        <style>
            :root {{
                --primary: {colors.get('primary', '#1A73E8')};
                --secondary: {colors.get('secondary', '#34A853')};
                --background: {colors.get('background', '#FFFFFF')};
                --surface: {colors.get('surface', '#F8F9FA')};
                --text-primary: {colors.get('text_primary', '#202124')};
                --text-secondary: {colors.get('text_secondary', '#5F6368')};
                --border: {colors.get('border', '#DADCE0')};
                --font-family: {fonts.get('family', 'Google Sans, sans-serif')};
                --max-width: {layout.get('max_width', '100%')};
                --border-radius: {layout.get('border_radius', '12px')};
            }}
            body {{
                font-family: var(--font-family);
                background-color: var(--background);
                color: var(--text-primary);
            }}
            .navbar {{
                background-color: var(--background);
                color: var(--text-primary);
                padding: 1rem 2rem;
                border-bottom: 1px solid var(--border);
                box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1.5rem;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1.5rem;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
            }}
            .card {{
                background: var(--surface);
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            }}
            .panel {{
                background: #F8F9FA;
                border-radius: 12px;
                padding: 1.5rem;
            }}
            .map-container {{
                border-radius: 12px;
                overflow: hidden;
                background: #E8F0FE;
                min-height: 400px;
            }}
        </style>
        """
