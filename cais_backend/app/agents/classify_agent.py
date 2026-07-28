#!/usr/bin/env python3
"""
CAIS Classify Agent (Service Account version)
Moves all files from the entire drive (or root) to a target folder
and renames them with category prefixes.
Uses service account authentication (no OAuth flow).
"""
import os
import sys
import time
import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# === CONFIGURATION ===
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/app/credentials/service-account.json')
TARGET_FOLDER_ID = '16ywo8njoZ4l7GYKBF1z9CPYQukrmqGVr'  # Replace with your folder ID
LOG_FILE = os.environ.get('LOG_FILE', '/app/logs/classify_drive_agent.log')

# === KEYWORD PREFIXES FOR RENAMING ===
KEYWORD_PREFIX = {
    'structural': '[STRUCTURAL] ',
    'beam': '[STRUCTURAL] ',
    'column': '[STRUCTURAL] ',
    'foundation': '[STRUCTURAL] ',
    'architect': '[ARCHITECTURAL] ',
    'plan': '[ARCHITECTURAL] ',
    'elevation': '[ARCHITECTURAL] ',
    'hvac': '[MECHANICAL] ',
    'duct': '[MECHANICAL] ',
    'mech': '[MECHANICAL] ',
    'elect': '[ELECTRICAL] ',
    'wiring': '[ELECTRICAL] ',
    'panel': '[ELECTRICAL] ',
    'plumb': '[PLUMBING] ',
    'pipe': '[PLUMBING] ',
    'drain': '[PLUMBING] ',
    'code': '[CODE] ',
    'standard': '[CODE] ',
    'ibc': '[CODE] ',
    'nfpa': '[CODE] ',
}

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def authenticate():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_file_prefix(filename):
    filename_lower = filename.lower()
    for keyword, prefix in KEYWORD_PREFIX.items():
        if keyword in filename_lower:
            return prefix
    return ""

def classify_files():
    drive_service = authenticate()
    try:
        folder = drive_service.files().get(fileId=TARGET_FOLDER_ID, fields="id,name").execute()
        logger.info(f"Target folder: {folder.get('name')} (ID: {TARGET_FOLDER_ID})")
        page_token = None
        moved = 0
        while True:
            response = drive_service.files().list(
                q="trashed=false",
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token
            ).execute()
            files = response.get("files", [])
            for file in files:
                if file["mimeType"] == "application/vnd.google-apps.folder":
                    continue
                prefix = get_file_prefix(file["name"])
                if prefix:
                    new_name = prefix + file["name"]
                    drive_service.files().update(
                        fileId=file["id"],
                        addParents=TARGET_FOLDER_ID,
                        removeParents="root",
                        body={"name": new_name},
                        fields="id,name"
                    ).execute()
                    moved += 1
                    logger.info(f"Moved: {file['name']} -> {new_name}")
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        logger.info(f"Total files classified and moved: {moved}")
    except HttpError as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    classify_files()
