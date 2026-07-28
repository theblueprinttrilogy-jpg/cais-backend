#!/usr/bin/env python3
"""
download_and_upload_oauth.py - Downloads codes from ICC using cookies + proxies.
"""

import os, sys, json, time, logging, requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIES_FILE = "/tmp/selenium_cookies.json"
DRIVE_CREDENTIALS = "/app/config/security/gdrive-credentials.json"
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "16ywo8njoZ4l7GYKBF1z9CPYQukrmqGVr")
ICC_BASE = "https://codes.iccsafe.org"
PROXY_URL = os.environ.get("PROXY_URL", "")
MAX_PDFS = 2

def load_cookies():
    if not os.path.exists(COOKIES_FILE):
        return {}
    with open(COOKIES_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {c['name']: c['value'] for c in data}
    return {}

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(DRIVE_CREDENTIALS,
        scopes=['https://www.googleapis.com/auth/drive.file'])
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, jurisdiction):
    service = get_drive_service()
    media = MediaFileUpload(str(file_path), mimetype='application/pdf', resumable=True)
    file = service.files().create(body={
        'name': file_path.name,
        'parents': [DRIVE_FOLDER_ID],
        'description': f"Jurisdiction: {jurisdiction}"
    }, media_body=media, fields='id').execute()
    return file.get('id')

def get_session(cookies):
    s = requests.Session()
    if PROXY_URL:
        s.proxies.update({'http': PROXY_URL, 'https': PROXY_URL})
        logger.info("Using proxy")
    for k,v in cookies.items():
        s.cookies.set(k, v)
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s

def find_code_pages(session, jurisdiction):
    url = f"{ICC_BASE}/search?q={jurisdiction}"
    try:
        r = session.get(url, timeout=120)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a.get('href') for a in soup.find_all('a', href=True) if '/content/' in a.get('href', '')]
        return [ICC_BASE + l if l.startswith('/') else l for l in links[:MAX_PDFS]]
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def download_pdf(session, page_url, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = session.get(page_url, timeout=120)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        pdf_link = None
        for a in soup.find_all('a', href=True):
            if a.get('href', '').lower().endswith('.pdf'):
                pdf_link = a.get('href')
                break
        if not pdf_link:
            for iframe in soup.find_all('iframe', src=True):
                if '.pdf' in iframe.get('src', ''):
                    pdf_link = iframe.get('src')
                    break
        if not pdf_link:
            return None
        if pdf_link.startswith('/'):
            pdf_link = ICC_BASE + pdf_link
        r2 = session.get(pdf_link, stream=True, timeout=120)
        if r2.status_code != 200:
            return None
        filename = pdf_link.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename = f"code_{int(time.time())}.pdf"
        filepath = output_dir / filename
        with open(filepath, 'wb') as f:
            for chunk in r2.iter_content(8192):
                f.write(chunk)
        return filepath
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

def process_jurisdiction(jurisdiction):
    logger.info(f"Processing {jurisdiction}")
    cookies = load_cookies()
    if not cookies:
        return {"success": False, "error": "No cookies"}
    session = get_session(cookies)
    pages = find_code_pages(session, jurisdiction)
    if not pages:
        return {"success": False, "error": "No code pages"}
    temp_dir = Path(f"/tmp/downloads/{jurisdiction.replace(' ', '_')}")
    downloaded = []
    for p in pages:
        pdf = download_pdf(session, p, temp_dir)
        if pdf:
            downloaded.append(pdf)
    if not downloaded:
        return {"success": False, "error": "No PDFs downloaded"}
    uploaded = []
    for pdf in downloaded:
        try:
            uploaded.append(upload_to_drive(pdf, jurisdiction))
        except Exception as e:
            logger.error(f"Upload error: {e}")
    return {"success": len(uploaded) > 0, "downloaded": len(downloaded), "uploaded": len(uploaded)}

if __name__ == "__main__":
    jur = sys.argv[1] if len(sys.argv) > 1 else "Florida"
    result = process_jurisdiction(jur)
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)
