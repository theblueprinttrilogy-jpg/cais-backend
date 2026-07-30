"""
Procore Skin - Corporate Style with Dense Tables and Organizational Blue

Procore presents a clean corporate interface, white and soft gray backgrounds,
with a blue visual line organizing navigation. Dense tables, metrics,
project cards, and separated modules.
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class ProcoreSkin(BaseSkin):
    """
    Procore marketplace skin.

    Style: Corporate, dense tables, organizational blue
    Type: Web-based construction management
    """

    def __init__(self):
        super().__init__("Procore", "web")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#0A2B5E",
                "secondary": "#2A6F97",
                "background": "#FFFFFF",
                "surface": "#F4F6F9",
                "text_primary": "#1A1A2E",
                "text_secondary": "#4A4A6A",
                "border": "#D1D5DB",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "error": "#EF4444",
                "navbar": "#0A2B5E",
                "table_header": "#F4F6F9",
                "table_stripe": "#FAFAFA",
                "card_shadow": "0 2px 8px rgba(0,0,0,0.08)"
            },
            "fonts": {
                "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                "heading": "Inter, sans-serif",
                "body": "Inter, sans-serif",
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
                "max_width": "1440px",
                "sidebar_width": "280px",
                "navbar_height": "64px",
                "spacing": "1.5rem",
                "border_radius": "8px"
            },
            "components": {
                "button": {
                    "padding": "0.5rem 1rem",
                    "border_radius": "4px",
                    "font_weight": "600"
                },
                "card": {
                    "padding": "1.5rem",
                    "border_radius": "8px",
                    "shadow": "0 2px 8px rgba(0,0,0,0.08)"
                },
                "table": {
                    "border": "1px solid #E2E8F0",
                    "header_bg": "#F4F6F9",
                    "stripe": "#FAFAFA"
                }
            }
        }

    def translate(self, language: str) -> Dict[str, Any]:
        """Translate the skin to the specified language."""
        self.language = language
        # In production, this would load translations
        return self.style_guide

    def render(self, translated_skin: Dict[str, Any]) -> str:
        """Render the interface with the adapted skin."""
        colors = translated_skin.get("colors", {})
        fonts = translated_skin.get("fonts", {})
        layout = translated_skin.get("layout", {})

        return f"""
        <style>
            :root {{
                --primary: {colors.get('primary', '#0A2B5E')};
                --secondary: {colors.get('secondary', '#2A6F97')};
                --background: {colors.get('background', '#FFFFFF')};
                --surface: {colors.get('surface', '#F4F6F9')};
                --text-primary: {colors.get('text_primary', '#1A1A2E')};
                --text-secondary: {colors.get('text_secondary', '#4A4A6A')};
                --border: {colors.get('border', '#D1D5DB')};
                --font-family: {fonts.get('family', 'Inter, sans-serif')};
                --max-width: {layout.get('max_width', '1440px')};
            }}
            body {{
                font-family: var(--font-family);
                background-color: var(--background);
                color: var(--text-primary);
            }}
            .navbar {{
                background-color: var(--primary);
                color: #FFFFFF;
                padding: 1rem;
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 4px;
                cursor: pointer;
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                color: #FFFFFF;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 4px;
                cursor: pointer;
            }}
            .card {{
                background: var(--surface);
                border-radius: 8px;
                padding: 1.5rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .table {{
                width: 100%;
                border-collapse: collapse;
                border: 1px solid var(--border);
            }}
            .table th {{
                background-color: var(--surface);
                font-weight: 600;
                padding: 0.75rem;
                text-align: left;
                border-bottom: 2px solid var(--border);
            }}
            .table td {{
                padding: 0.75rem;
                border-bottom: 1px solid var(--border);
            }}
            .table tr:nth-child(even) {{
                background-color: #FAFAFA;
            }}
        </style>
        """
