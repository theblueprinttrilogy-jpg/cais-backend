import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load environment variables from .env file
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in .env file.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    cred = flow.run_local_server(port=0)
    
    print("\n--- AUTHENTICATION SUCCESSFUL ---")
    print(f"Your new GOOGLE_REFRESH_TOKEN is:\n{cred.refresh_token}\n")
    print("Copy this refresh token and update your .env file.")

if __name__ == "__main__":
    main()
