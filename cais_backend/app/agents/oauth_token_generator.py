import argparse
import json
import logging
import os
import sys
from typing import Dict, Any

import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/drive"]

def main():
    parser = argparse.ArgumentParser(description="Generate OAuth 2.0 Refresh Token for Google Drive.")
    parser.add_argument("--client-id", required=True, help="OAuth client ID.")
    parser.add_argument("--client-secret", required=True, help="OAuth client secret.")
    parser.add_argument("--port", type=int, default=8085, help="Local server port.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    client_config = {
        "installed": {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
            "redirect_uris": [f"http://localhost:{args.port}/"]
        }
    }

    try:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
        flow.redirect_uri = f"http://localhost:{args.port}/"
        
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
        
        print("\n" + "=" * 70)
        print("OPEN THIS URL IN YOUR WINDOWS BROWSER:")
        print("=" * 70)
        print(auth_url)
        print("=" * 70 + "\n")

        credentials = flow.run_local_server(port=args.port, open_browser=False)
        
        output = {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "refresh_token": credentials.refresh_token,
            "token_uri": TOKEN_URI,
            "scopes": SCOPES,
        }
        print("\n" + "=" * 70)
        print("REFRESH TOKEN GENERATED SUCCESSFULLY:")
        print(json.dumps(output, indent=2))
        print("=" * 70)
    except Exception as e:
        logger.error(f"Token generation failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
