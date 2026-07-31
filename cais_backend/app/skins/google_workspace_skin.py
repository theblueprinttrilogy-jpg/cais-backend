"""
Google Workspace Skin - Lightweight Collaborative Style

Google Workspace has a familiar and lightweight look, with email, document,
and apps interfaces grouped in a clean environment.
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class GoogleWorkspaceSkin(BaseSkin):
    """
    Google Workspace marketplace skin.

    Style: Lightweight, collaborative, Google colors
    Type: Web-based productivity suite
    """

    def __init__(self):
        super().__init__("Google Workspace", "web")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#1A73E8",
                "secondary": "#EA4335",
                "background": "#FFFFFF",
                "surface": "#F8F9FA",
                "text_primary": "#202124",
                "text_secondary": "#5F6368",
                "border": "#DADCE0",
                "success": "#34A853",
                "warning": "#FBBC04",
                "error": "#EA4335",
                "navbar": "#FFFFFF",
                "card_shadow": "0 1px 4px rgba(0,0,0,0.04)"
            },
            "fonts": {
                "family": "Google Sans, Roboto, -apple-system, sans-serif",
                "heading": "Google Sans, sans-serif",
                "body": "Roboto, sans-serif",
                "mono": "Google Sans Mono, monospace",
                "sizes": {
                    "xs": "0.7rem",
                    "sm": "0.85rem",
                    "base": "1rem",
                    "lg": "1.1rem",
                    "xl": "1.25rem",
                    "2xl": "1.5rem",
                    "3xl": "1.75rem"
                }
            },
            "layout": {
                "max_width": "100%",
                "sidebar_width": "200px",
                "navbar_height": "64px",
                "spacing": "1.25rem",
                "border_radius": "8px"
            },
            "components": {
                "button": {
                    "padding": "0.5rem 1.25rem",
                    "border_radius": "8px",
                    "font_weight": "500"
                },
                "card": {
                    "padding": "1rem 1.25rem",
                    "border_radius": "8px",
                    "shadow": "0 1px 4px rgba(0,0,0,0.04)"
                },
                "app_icon": {
                    "border_radius": "12px",
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
                --primary: {colors.get('primary', '#1A73E8')};
                --secondary: {colors.get('secondary', '#EA4335')};
                --background: {colors.get('background', '#FFFFFF')};
                --surface: {colors.get('surface', '#F8F9FA')};
                --text-primary: {colors.get('text_primary', '#202124')};
                --text-secondary: {colors.get('text_secondary', '#5F6368')};
                --border: {colors.get('border', '#DADCE0')};
                --font-family: {fonts.get('family', 'Google Sans, Roboto, sans-serif')};
            }}
            body {{
                font-family: var(--font-family);
                background-color: var(--background);
                color: var(--text-primary);
            }}
            .navbar {{
                background-color: var(--surface);
                color: var(--text-primary);
                padding: 0.75rem 1.5rem;
                border-bottom: 1px solid var(--border);
                display: flex;
                align-items: center;
                gap: 1rem;
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1.25rem;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
            }}
            .btn-primary:hover {{
                background-color: #1557B0;
            }}
            .btn-secondary {{
                background-color: transparent;
                color: var(--primary);
                border: 1px solid var(--border);
                padding: 0.5rem 1.25rem;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
            }}
            .btn-secondary:hover {{
                background-color: var(--surface);
            }}
            .card {{
                background: var(--surface);
                border-radius: 8px;
                padding: 1rem 1.25rem;
                box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            }}
            .app-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
                gap: 1rem;
            }}
            .app-icon {{
                border-radius: 12px;
                padding: 0.5rem;
                text-align: center;
                cursor: pointer;
                transition: background 0.2s;
            }}
            .app-icon:hover {{
                background: var(--surface);
            }}
            .app-icon .icon {{
                font-size: 2rem;
                display: block;
            }}
            .app-icon .label {{
                font-size: 0.75rem;
                color: var(--text-secondary);
                margin-top: 0.25rem;
                display: block;
            }}
        </style>
        """
