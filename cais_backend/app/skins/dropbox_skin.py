"""
Dropbox Skin - Minimalist and Clean with List View

Dropbox has a minimalist and very clean interface, centered on a list of
folders and files, with a simple sidebar and plenty of white space.
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class DropboxSkin(BaseSkin):
    """
    Dropbox marketplace skin.

    Style: Minimalist, clean, list view
    Type: Web-based file storage
    """

    def __init__(self):
        super().__init__("Dropbox", "web")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#0061FF",
                "secondary": "#A2B1C6",
                "background": "#FFFFFF",
                "surface": "#F8F8FA",
                "text_primary": "#1A1A2E",
                "text_secondary": "#6B6B80",
                "border": "#E0E0E0",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "error": "#EF4444",
                "navbar": "#FFFFFF",
                "sidebar": "#F8F8FA",
                "card_shadow": "none"
            },
            "fonts": {
                "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                "heading": "-apple-system, BlinkMacSystemFont, sans-serif",
                "body": "-apple-system, BlinkMacSystemFont, sans-serif",
                "mono": "SF Mono, monospace",
                "sizes": {
                    "xs": "0.7rem",
                    "sm": "0.8rem",
                    "base": "0.9rem",
                    "lg": "1rem",
                    "xl": "1.1rem",
                    "2xl": "1.25rem",
                    "3xl": "1.5rem"
                }
            },
            "layout": {
                "max_width": "100%",
                "sidebar_width": "240px",
                "navbar_height": "48px",
                "spacing": "1rem",
                "border_radius": "0px"
            },
            "components": {
                "button": {
                    "padding": "0.3rem 0.8rem",
                    "border_radius": "4px",
                    "font_weight": "400"
                },
                "card": {
                    "padding": "0.5rem",
                    "border_radius": "0px",
                    "shadow": "none"
                },
                "list": {
                    "border": "none",
                    "padding": "0.25rem 0"
                },
                "file_item": {
                    "padding": "0.5rem 0.75rem",
                    "border_radius": "4px",
                    "hover_bg": "#F0F0F0"
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
                --primary: {colors.get('primary', '#0061FF')};
                --secondary: {colors.get('secondary', '#A2B1C6')};
                --background: {colors.get('background', '#FFFFFF')};
                --surface: {colors.get('surface', '#F8F8FA')};
                --text-primary: {colors.get('text_primary', '#1A1A2E')};
                --text-secondary: {colors.get('text_secondary', '#6B6B80')};
                --border: {colors.get('border', '#E0E0E0')};
                --font-family: {fonts.get('family', '-apple-system, sans-serif')};
                --hover-bg: {colors.get('file_item', {}).get('hover_bg', '#F0F0F0')};
            }}
            body {{
                font-family: var(--font-family);
                background-color: var(--background);
                color: var(--text-primary);
                font-size: 0.9rem;
            }}
            .navbar {{
                background-color: var(--background);
                color: var(--text-primary);
                padding: 0.5rem 1.5rem;
                border-bottom: 1px solid var(--border);
            }}
            .sidebar {{
                background-color: var(--surface);
                padding: 1rem;
                width: 240px;
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 0.3rem 0.8rem;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.85rem;
            }}
            .btn-secondary {{
                background-color: transparent;
                color: var(--text-secondary);
                border: none;
                padding: 0.3rem 0.8rem;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.85rem;
            }}
            .btn-secondary:hover {{
                background-color: var(--surface);
            }}
            .card {{
                background: var(--surface);
                padding: 0.5rem;
            }}
            .file-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .file-item {{
                padding: 0.5rem 0.75rem;
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}
            .file-item:hover {{
                background-color: var(--hover-bg);
            }}
            .file-item .icon {{
                color: var(--secondary);
                font-size: 1.2rem;
            }}
            .file-item .name {{
                flex: 1;
            }}
            .file-item .size {{
                color: var(--text-secondary);
                font-size: 0.8rem;
            }}
        </style>
        """
