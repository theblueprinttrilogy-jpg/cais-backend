"""
AppStore Skin - iOS Native Style with CAIS Branding

AppStore uses the official CAIS CODE COMPLIANCE branding:
- Logo: "C" in black with fire orange center
- Front view: Brown clipboard with white notepad and green checkmark
- In front of checkmark: Surveyor's theodolite on tripod
- Below image: "CAIS" (full width)
- Below that: "CODE COMPLIANCE" (full width)
"""

from typing import Dict, Any
from app.skins.base_skin import BaseSkin


class AppStoreSkin(BaseSkin):
    """
    AppStore marketplace skin.

    Style: iOS native, minimalist, elegant
    Type: Mobile application
    Branding: Official CAIS CODE COMPLIANCE logo
    """

    def __init__(self):
        super().__init__("AppStore", "mobile")
        self.style_guide = self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": "#000000",
                "secondary": "#FF6B00",
                "background": "#F2F2F7",
                "surface": "#FFFFFF",
                "text_primary": "#000000",
                "text_secondary": "#8E8E93",
                "border": "#E5E5EA",
                "success": "#34C759",
                "warning": "#FF9500",
                "error": "#FF3B30",
                "navbar": "#F2F2F7",
                "tab_bar": "#F2F2F7"
            },
            "fonts": {
                "family": "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif",
                "heading": "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
                "body": "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
                "sizes": {
                    "xs": "11px",
                    "sm": "13px",
                    "base": "15px",
                    "lg": "17px",
                    "xl": "20px",
                    "2xl": "24px",
                    "3xl": "30px"
                }
            },
            "layout": {
                "max_width": "100%",
                "sidebar_width": "0px",
                "navbar_height": "44px",
                "spacing": "16px",
                "border_radius": "12px"
            },
            "components": {
                "button": {
                    "padding": "10px 20px",
                    "border_radius": "10px",
                    "font_weight": "600"
                },
                "card": {
                    "padding": "16px",
                    "border_radius": "12px",
                    "shadow": "0 2px 10px rgba(0,0,0,0.05)"
                },
                "badge": {
                    "border_radius": "12px",
                    "padding": "4px 12px"
                }
            },
            "branding": {
                "logo": {
                    "letter": "C",
                    "color": "#000000",
                    "center": "#FF6B00",
                    "description": "Letter C in black with fire orange center"
                },
                "clipboard": {
                    "color": "#8B6914",
                    "description": "Brown clipboard"
                },
                "notepad": {
                    "color": "#FFFFFF",
                    "description": "White notepad"
                },
                "checkmark": {
                    "color": "#00C853",
                    "description": "Green checkmark"
                },
                "theodolite": {
                    "description": "Surveyor's theodolite mounted on tripod"
                },
                "text": {
                    "cais": "CAIS",
                    "code_compliance": "CODE COMPLIANCE"
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
        branding = translated_skin.get("branding", {})

        logo = branding.get("logo", {})
        text = branding.get("text", {})

        return f"""
        <style>
            :root {{
                --primary: {colors.get('primary', '#000000')};
                --secondary: {colors.get('secondary', '#FF6B00')};
                --background: {colors.get('background', '#F2F2F7')};
                --surface: {colors.get('surface', '#FFFFFF')};
                --text-primary: {colors.get('text_primary', '#000000')};
                --text-secondary: {colors.get('text_secondary', '#8E8E93')};
                --border: {colors.get('border', '#E5E5EA')};
                --font-family: {fonts.get('family', '-apple-system, sans-serif')};
            }}
            body {{
                font-family: var(--font-family);
                background-color: var(--background);
                color: var(--text-primary);
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }}
            .branding-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px 0;
            }}
            .branding-logo {{
                position: relative;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .branding-logo .letter {{
                font-size: 48px;
                font-weight: 900;
                color: {logo.get('color', '#000000')};
                position: relative;
            }}
            .branding-logo .letter::after {{
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 20px;
                height: 20px;
                background: {logo.get('center', '#FF6B00')};
                border-radius: 50%;
                opacity: 0.8;
                z-index: -1;
            }}
            .branding-clipboard {{
                font-size: 30px;
                margin: 5px 0;
                color: {branding.get('clipboard', {}).get('color', '#8B6914')};
            }}
            .branding-theodolite {{
                font-size: 30px;
                margin: 5px 0;
                display: block;
            }}
            .branding-text {{
                text-align: center;
                margin-top: 10px;
            }}
            .branding-text .cais {{
                font-size: 24px;
                font-weight: 900;
                letter-spacing: 4px;
                color: var(--text-primary);
                display: block;
            }}
            .branding-text .code-compliance {{
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 2px;
                color: var(--secondary);
                display: block;
            }}
            .navbar {{
                background-color: var(--background);
                padding: 8px 16px;
                border-bottom: 1px solid var(--border);
            }}
            .btn-primary {{
                background-color: var(--primary);
                color: #FFFFFF;
                border: none;
                padding: 10px 20px;
                border-radius: 10px;
                font-weight: 600;
                cursor: pointer;
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                color: #FFFFFF;
                border: none;
                padding: 10px 20px;
                border-radius: 10px;
                font-weight: 600;
                cursor: pointer;
            }}
            .card {{
                background: var(--surface);
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            .badge {{
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            .badge-success {{
                background-color: {colors.get('success', '#34C759')};
                color: #FFFFFF;
            }}
        </style>
        """
