"""
Chameleon Engine - Visual Adaptation for 21 Marketplaces

Automatically loads the visual "skin" of the corresponding marketplace
and adapts the entire interface to the user's language.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 1.2

AppStore and GooglePlay use the official CAIS CODE COMPLIANCE branding:
- Logo: "C" in black with fire orange center
- Front view: Brown clipboard with white notepad and green checkmark
- In front of checkmark: Surveyor's theodolite on tripod
- Below image: "CAIS" (full width)
- Below that: "CODE COMPLIANCE" (full width)
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ChameleonEngine:
    """
    Chameleon Engine - Visual Adaptation.

    Supported marketplaces:
    1. Procore, 2. Autodesk Forma, 3. Oracle Aconex, 4. Bentley iTwin,
    5. PlanGrid, 6. Fieldwire, 7. Buildertrend, 8. Newforma,
    9. SharePoint, 10. Dropbox, 11. Google Workspace, 12. ServiceTitan,
    13. Simpro, 14. Esri ArcGIS, 15. Cityworks, 16. Revit,
    17. AutoCAD, 18. Bluebeam Revu, 19. Accela, 20. AppStore, 21. GooglePlay
    """

    SUPPORTED_PLATFORMS = [
        "procore", "autodesk_forma", "oracle_aconex", "bentley_itwin",
        "plangrid", "fieldwire", "buildertrend", "newforma",
        "sharepoint", "dropbox", "google_workspace", "servicetitan",
        "simpro", "esri_arcgis", "cityworks", "revit",
        "autocad", "bluebeam_revu", "accela", "appstore", "googleplay"
    ]

    PLATFORM_STYLES = {
        "procore": {"primary": "#0A2B5E", "secondary": "#2A6F97", "type": "corporate", "bg": "#FFFFFF", "text": "#1A1A2E"},
        "autodesk_forma": {"primary": "#1A73E8", "secondary": "#34A853", "type": "modern", "bg": "#FFFFFF", "text": "#202124"},
        "oracle_aconex": {"primary": "#C74634", "secondary": "#FDB81B", "type": "enterprise", "bg": "#F8F9FA", "text": "#1A1A2E"},
        "bentley_itwin": {"primary": "#0057A3", "secondary": "#00A3E0", "type": "technical", "bg": "#1A1A2E", "text": "#FFFFFF"},
        "plangrid": {"primary": "#00A3E0", "secondary": "#0057A3", "type": "document", "bg": "#F5F5F5", "text": "#1A1A2E"},
        "fieldwire": {"primary": "#F5A623", "secondary": "#4A90D9", "type": "mobile", "bg": "#FFFFFF", "text": "#1A1A2E"},
        "buildertrend": {"primary": "#008A45", "secondary": "#F5A623", "type": "dashboard", "bg": "#F8FAFC", "text": "#1A1A2E"},
        "newforma": {"primary": "#003366", "secondary": "#4A90D9", "type": "corporate", "bg": "#FFFFFF", "text": "#1A1A2E"},
        "sharepoint": {"primary": "#0078D4", "secondary": "#00A3E0", "type": "portal", "bg": "#FFFFFF", "text": "#1A1A2E"},
        "dropbox": {"primary": "#0061FF", "secondary": "#A2B1C6", "type": "minimal", "bg": "#FFFFFF", "text": "#1A1A2E"},
        "google_workspace": {"primary": "#1A73E8", "secondary": "#EA4335", "type": "collaborative", "bg": "#FFFFFF", "text": "#202124"},
        "servicetitan": {"primary": "#00A3E0", "secondary": "#F5A623", "type": "operational", "bg": "#F8FAFC", "text": "#1A1A2E"},
        "simpro": {"primary": "#008A45", "secondary": "#4A90D9", "type": "operational", "bg": "#FFFFFF", "text": "#1A1A2E"},
        "esri_arcgis": {"primary": "#008A45", "secondary": "#4A90D9", "type": "geospatial", "bg": "#F0F0F0", "text": "#1A1A2E"},
        "cityworks": {"primary": "#003366", "secondary": "#4A90D9", "type": "municipal", "bg": "#F8F9FA", "text": "#1A1A2E"},
        "revit": {"primary": "#00A3E0", "secondary": "#0057A3", "type": "bim", "bg": "#2C2C2C", "text": "#FFFFFF"},
        "autocad": {"primary": "#C74634", "secondary": "#FDB81B", "type": "cad", "bg": "#1A1A2E", "text": "#FFFFFF"},
        "bluebeam_revu": {"primary": "#003366", "secondary": "#00A3E0", "type": "pdf", "bg": "#F5F5F5", "text": "#1A1A2E"},
        "accela": {"primary": "#0057A3", "secondary": "#2A6F97", "type": "administrative", "bg": "#F8F9FA", "text": "#1A1A2E"},
        "appstore": {
            "primary": "#000000",
            "secondary": "#FF6B00",
            "type": "ios",
            "bg": "#F2F2F7",
            "text": "#000000",
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
        },
        "googleplay": {
            "primary": "#000000",
            "secondary": "#FF6B00",
            "type": "android",
            "bg": "#FFFFFF",
            "text": "#202124",
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
    }

    def __init__(self):
        self.current_platform: Optional[str] = None
        self.current_style: Optional[Dict] = None
        self.current_language: str = "en"

    def adapt_interface(self, platform: str, user_language: str = "en") -> Dict[str, Any]:
        """
        Adapt the interface to the specified platform and language.

        Args:
            platform: The marketplace identifier
            user_language: The language code

        Returns:
            dict: The adapted interface configuration
        """
        platform = platform.lower()

        if platform not in self.SUPPORTED_PLATFORMS:
            logger.warning(f"Platform '{platform}' not supported. Using default.")
            platform = "procore"

        self.current_platform = platform
        self.current_language = user_language
        self.current_style = self.PLATFORM_STYLES.get(platform, self.PLATFORM_STYLES["procore"])

        logger.info(f"Adapted interface for platform: {platform}, language: {user_language}")

        return {
            "platform": platform,
            "language": user_language,
            "style": self.current_style,
            "skin": self._generate_skin_html()
        }

    def _generate_skin_html(self) -> str:
        """Generate HTML/CSS for the skin."""
        if not self.current_style:
            return ""

        style = self.current_style

        # For AppStore and GooglePlay, include the full branding
        if self.current_platform in ["appstore", "googleplay"]:
            return self._generate_marketplace_branding(style)

        return f"""
        <style>
            :root {{
                --primary: {style['primary']};
                --secondary: {style['secondary']};
                --bg: {style['bg']};
                --text: {style['text']};
                --type: {style['type']};
            }}
            body {{
                background-color: var(--bg);
                color: var(--text);
            }}
            .navbar {{
                background-color: var(--primary);
                color: #FFFFFF;
            }}
            .btn-primary {{
                background-color: var(--primary);
                border-color: var(--primary);
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                border-color: var(--secondary);
            }}
        </style>
        """

    def _generate_marketplace_branding(self, style: Dict) -> str:
        """Generate HTML/CSS for AppStore and GooglePlay branding."""
        branding = style.get("branding", {})
        logo = branding.get("logo", {})
        clipboard = branding.get("clipboard", {})
        notepad = branding.get("notepad", {})
        checkmark = branding.get("checkmark", {})
        theodolite = branding.get("theodolite", {})
        text = branding.get("text", {})

        return f"""
        <style>
            :root {{
                --primary: {style['primary']};
                --secondary: {style['secondary']};
                --bg: {style['bg']};
                --text: {style['text']};
                --type: {style['type']};
            }}
            body {{
                background-color: var(--bg);
                color: var(--text);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            .cais-branding {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .cais-logo-container {{
                position: relative;
                width: 120px;
                height: 120px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 15px;
            }}
            .cais-logo-letter {{
                font-size: 80px;
                font-weight: 900;
                color: {logo.get('color', '#000000')};
                position: relative;
            }}
            .cais-logo-letter::after {{
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 30px;
                height: 30px;
                background: {logo.get('center', '#FF6B00')};
                border-radius: 50%;
                opacity: 0.8;
                z-index: -1;
            }}
            .cais-icon-clipboard {{
                font-size: 40px;
                margin: 10px 0;
                color: {clipboard.get('color', '#8B6914')};
                position: relative;
            }}
            .cais-icon-clipboard .notepad {{
                display: inline-block;
                background: {notepad.get('color', '#FFFFFF')};
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 14px;
                color: #000;
                margin: 0 5px;
            }}
            .cais-icon-clipboard .checkmark {{
                color: {checkmark.get('color', '#00C853')};
                font-size: 24px;
                margin: 0 5px;
            }}
            .cais-theodolite {{
                font-size: 40px;
                margin: 5px 0;
                display: block;
            }}
            .cais-text-brand {{
                text-align: center;
                width: 100%;
                margin-top: 10px;
            }}
            .cais-text-brand .cais-main {{
                font-size: 32px;
                font-weight: 900;
                letter-spacing: 4px;
                color: var(--primary);
                display: block;
                width: 100%;
                text-align: center;
            }}
            .cais-text-brand .cais-sub {{
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 3px;
                color: var(--secondary);
                display: block;
                width: 100%;
                text-align: center;
            }}
            .navbar {{
                background-color: var(--primary);
                color: #FFFFFF;
            }}
            .btn-primary {{
                background-color: var(--primary);
                border-color: var(--primary);
            }}
            .btn-secondary {{
                background-color: var(--secondary);
                border-color: var(--secondary);
            }}
        </style>
        <div class="cais-branding">
            <div class="cais-logo-container">
                <span class="cais-logo-letter">{logo.get('letter', 'C')}</span>
            </div>
            <div class="cais-icon-clipboard">
                <span class="notepad">📋</span>
                <span class="checkmark">✓</span>
            </div>
            <span class="cais-theodolite">🔭</span>
            <div class="cais-text-brand">
                <span class="cais-main">{text.get('cais', 'CAIS')}</span>
                <span class="cais-sub">{text.get('code_compliance', 'CODE COMPLIANCE')}</span>
            </div>
        </div>
        """

    def get_style(self, platform: str) -> Optional[Dict]:
        """Get the style for a specific platform."""
        return self.PLATFORM_STYLES.get(platform.lower())

    def get_supported_platforms(self) -> list:
        """Get the list of supported platforms."""
        return self.SUPPORTED_PLATFORMS

    def get_platform_type(self, platform: str) -> str:
        """Get the type of a platform."""
        style = self.get_style(platform)
        return style.get("type", "unknown") if style else "unknown"

    def get_marketplace_branding(self, platform: str) -> Optional[Dict]:
        """Get the branding for a specific marketplace."""
        style = self.get_style(platform)
        if style and platform in ["appstore", "googleplay"]:
            return style.get("branding")
        return None
