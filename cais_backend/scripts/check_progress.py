#!/usr/bin/env python3
# scripts/check_progress.py - CAIS v2.0 Colony & Janitor Progress Monitor

import os
import json
from pathlib import Path
from datetime import datetime

def check_progress():
    print("=" * 60)
    print("CAIS v2.0 - COLONY & JANITOR PROGRESS MONITOR")
    print(f"Timestamp: {datetime.utcnow().isoformat()} UTC")
    print("=" * 60)

    # 1. Check logs directory
    log_dir = Path("logs")
    if log_dir.exists():
        print("\n[+] Log Files Found:")
        for log_file in log_dir.glob("*.log"):
            size = log_file.stat().st_size
            print(f"  - {log_file.name} ({size} bytes)")
    else:
        print("\n[-] 'logs' directory not found.")

    # 2. Check colony output / storage
    colony_dir = Path("colony_output")
    if colony_dir.exists():
        print("\n[+] Colony Output Storage:")
        files = list(colony_dir.glob("**/*"))
        print(f"  - Total files/artifacts: {len(files)}")
    else:
        print("\n[-] 'colony_output' directory not found.")

    # 3. Check cookies persistence
    cookies_dir = Path("cookies")
    if cookies_dir.exists():
        print("\n[+] Cookie Persistence Engine:")
        for cookie_file in cookies_dir.glob("*.pkl"):
            print(f"  - Active Session File: {cookie_file.name}")
    else:
        print("\n[-] 'cookies' directory not found.")

    # 4. Check secrets / credentials for Janitor
    secrets_dir = Path("secrets")
    if secrets_dir.exists():
        print("\n[+] Secrets Directory:")
        creds = list(secrets_dir.glob("*"))
        if creds:
            for c in creds:
                print(f"  - Credential file: {c.name}")
        else:
            print("  - ⚠️ Secrets directory is empty (Janitor OAuth credentials needed).")
    else:
        print("\n[-] 'secrets' directory not found.")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_progress()
