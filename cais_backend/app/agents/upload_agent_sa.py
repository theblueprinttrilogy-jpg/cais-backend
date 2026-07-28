#!/usr/bin/env python3
"""
Upload Agent for Google Drive using Service Account (no OAuth).
Uploads all files from a local folder to a specified Google Drive folder.
"""
import os
import sys
import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === CONFIGURATION ===
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/app/credentials/service-account.json')
SOURCE_FOLDER = os.environ.get('SOURCE_FOLDER', '/data')
TARGET_FOLDER_ID = os.environ.get('TARGET_FOLDER_ID', 'root')  # 'root' or a folder ID
LOG_FILE = os.environ.get('LOG_FILE', '/app/logs/upload_agent.log')

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

def upload_file(drive_service, file_path, parent_id):
    file_name = os.path.basename(file_path)
    file_metadata = {'name': file_name, 'parents': [parent_id]}
    media = MediaFileUpload(file_path, resumable=True)
    try:
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"Uploaded: {file_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_name}: {e}")
        return False

def upload_folder(drive_service, local_path, parent_id):
    folder_name = os.path.basename(local_path)
    folder_metadata = {
        'name': folder_name,
        'parents': [parent_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    try:
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')
        logger.info(f"Created folder: {folder_name} (ID: {folder_id})")
        return folder_id
    except Exception as e:
        logger.error(f"Failed to create folder {folder_name}: {e}")
        return None

def walk_and_upload(drive_service, local_path, parent_id):
    for root, dirs, files in os.walk(local_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            upload_file(drive_service, file_path, parent_id)

def main():
    logger.info("Starting Upload Agent (Service Account)")
    logger.info(f"Source folder: {SOURCE_FOLDER}")
    if not os.path.exists(SOURCE_FOLDER):
        logger.error(f"Source folder does not exist: {SOURCE_FOLDER}")
        sys.exit(1)
    drive_service = authenticate()
    parent_id = TARGET_FOLDER_ID
    if TARGET_FOLDER_ID == 'root':
        parent_id = 'root'
    upload_folder(drive_service, SOURCE_FOLDER, parent_id)
    walk_and_upload(drive_service, SOURCE_FOLDER, parent_id)
    logger.info("Upload completed.")

if __name__ == "__main__":
    main()
