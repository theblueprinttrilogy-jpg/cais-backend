"""
PlanGrid Skin - Document-Oriented with Technical Drawings

PlanGrid has an interface very oriented to plans, with a typical capture showing
a tablet or viewer with a technical drawing background and overlaid menus.
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class PlanGridSkin(BaseSkin):
    """
    PlanGrid marketplace skin.

    Style: Document-oriented, technical drawings
    Type: Web/mobile plan viewing
    """

    def __init__(self):
        super().__init__("PlanGrid", "web")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#00A3E0",
                "secondary": "#0057A3",
                "background": "#F5F5F5",
                "surface": "#FFFFFF",
                "text_primary": "#1A1A2E",
                "text_secondary": "#6B6B80",
                "border": "#E0E0E0",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "error": "#EF4444",
                "navbar": "#FFFFFF",
                "drawing_bg": "#E8E8E8",
                "measurement": "#FF6B00"
            },
            "fonts": {
                "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                "heading": "Inter, sans-serif",
                "body": "Inter, sans-serif",
                "mono": "JetBrains Mono, monospace",
                "sizes": {
                    "xs": "0.7rem",
                    "sm": "0.8rem",
                    "base": "0.95rem",
                    "lg": "1.05rem",
                    "xl": "1.2rem",
                    "2xl": "1.4rem"
                }
            },
            "layout": {
                "max_width": "100%",
                "sidebar_width": "280px",
                "navbar_height": "56px",
                "spacing": "1rem",
                "border_radius": "4px"
            },
            "components": {
                "button": {
                    "padding": "0.4rem 1rem",
                    "border_radius": "4px",
                    "font_weight": "500"
                },
                "card": {
                    "padding": "1rem",
                    "border_radius": "4px",
                    "shadow": "0 1px 4px rgba(0,0,0,0.06)"
                },
                "drawing": {
                    "background": "#E8E8E8",
                    "border": "1px solid #D0D0D0"
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
                --primary: {colors.get('primary', '#00A3E0')};
                --secondary: {colors.get('secondary', '#0057A3')};
                --background: {colors.get('background', '#F5F5F5')};
                --surface: {colors.get('surface', '#FFFFFF')};
                --text-primary: {colors.get('text_primary', '#1A1A2E')};
                --text-secondary: {colors.get('text_secondary', '#6B6B80')};
                --border: {colors.get('border', '#E0E0E0')};
                --font-family: {fonts.get('family', 'Inter, sans-serif')};
                --measurement: {colors.get('measurement', '#FF6B00')};
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
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 0.4rem 1rem;
                border-radius: 4px;
                font-weight: 500;
                cursor: pointer;
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                color: #FFFFFF;
                border: none;
                padding: 0.4rem 1rem;
                border-radius: 4px;
                font-weight: 500;
                cursor: pointer;
            }}
            .card {{
                background: var(--surface);
                border-radius: 4px;
                padding: 1rem;
                box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            }}
            .drawing-container {{
                background: #E8E8E8;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                min-height: 500px;
                position: relative;
            }}
            .measurement {{
                color: var(--measurement);
                font-weight: 600;
            }}
            .overlay-menu {{
                background: rgba(255,255,255,0.95);
                border-radius: 4px;
                padding: 0.5rem 1rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                position: absolute;
                top: 1rem;
                left: 1rem;
            }}
        </style>
        """
