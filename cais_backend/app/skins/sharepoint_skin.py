"""
SharePoint Skin - Corporate Portal with Microsoft Style

SharePoint looks like a Microsoft corporate portal: white dominant, blue accents,
side or top navigation, and well-separated content blocks.
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class SharePointSkin(BaseSkin):
    """
    SharePoint marketplace skin.

    Style: Corporate portal, Microsoft style
    Type: Web-based document management
    """

    def __init__(self):
        super().__init__("SharePoint", "web")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#0078D4",
                "secondary": "#00A3E0",
                "background": "#FFFFFF",
                "surface": "#F3F6F9",
                "text_primary": "#1A1A2E",
                "text_secondary": "#4A4A6A",
                "border": "#D1D5DB",
                "success": "#107C10",
                "warning": "#F5A623",
                "error": "#D13438",
                "navbar": "#0078D4",
                "sidebar": "#F3F6F9",
                "card_shadow": "0 1px 4px rgba(0,0,0,0.08)"
            },
            "fonts": {
                "family": "Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif",
                "heading": "Segoe UI, sans-serif",
                "body": "Segoe UI, sans-serif",
                "mono": "Consolas, monospace",
                "sizes": {
                    "xs": "0.75rem",
                    "sm": "0.875rem",
                    "base": "1rem",
                    "lg": "1.125rem",
                    "xl": "1.25rem",
                    "2xl": "1.5rem",
                    "3xl": "2rem"
                }
            },
            "layout": {
                "max_width": "100%",
                "sidebar_width": "280px",
                "navbar_height": "60px",
                "spacing": "1.5rem",
                "border_radius": "4px"
            },
            "components": {
                "button": {
                    "padding": "0.5rem 1.25rem",
                    "border_radius": "4px",
                    "font_weight": "400"
                },
                "card": {
                    "padding": "1.5rem",
                    "border_radius": "4px",
                    "shadow": "0 1px 4px rgba(0,0,0,0.08)"
                },
                "list": {
                    "border": "1px solid #D1D5DB",
                    "padding": "0.5rem"
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

        return f"""
        <style>
            :root {{
                --primary: {colors.get('primary', '#0078D4')};
                --secondary: {colors.get('secondary', '#00A3E0')};
                --background: {colors.get('background', '#FFFFFF')};
                --surface: {colors.get('surface', '#F3F6F9')};
                --text-primary: {colors.get('text_primary', '#1A1A2E')};
                --text-secondary: {colors.get('text_secondary', '#4A4A6A')};
                --border: {colors.get('border', '#D1D5DB')};
                --font-family: {fonts.get('family', 'Segoe UI, sans-serif')};
            }}
            body {{
                font-family: var(--font-family);
                background-color: var(--background);
                color: var(--text-primary);
            }}
            .navbar {{
                background-color: var(--primary);
                color: #FFFFFF;
                padding: 0.75rem 2rem;
                box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            }}
            .navbar a {{
                color: #FFFFFF;
                text-decoration: none;
            }}
            .sidebar {{
                background-color: var(--surface);
                border-right: 1px solid var(--border);
                padding: 1rem;
                height: 100%;
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1.25rem;
                border-radius: 4px;
                cursor: pointer;
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1.25rem;
                border-radius: 4px;
                cursor: pointer;
            }}
            .card {{
                background: var(--surface);
                border-radius: 4px;
                padding: 1.5rem;
                box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            }}
            .list-item {{
                border-bottom: 1px solid var(--border);
                padding: 0.5rem;
            }}
            .list-item:last-child {{
                border-bottom: none;
            }}
        </style>
        """
