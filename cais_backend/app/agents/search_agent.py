#!/usr/bin/env python3
"""
search_agent.py - Individual search agent.
"""

import sys, json, subprocess, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOWNLOAD_SCRIPT = "/app/agents/download_and_upload_oauth.py"

def run_download(jurisdiction_name):
    try:
        result = subprocess.run(
            [sys.executable, DOWNLOAD_SCRIPT, jurisdiction_name],
            capture_output=True, text=True, timeout=300
        )
        return {"success": result.returncode == 0}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    input_j = sys.argv[1] if len(sys.argv) > 1 else "{}"
    try:
        data = json.loads(input_j)
        name = data.get('state') or data.get('country') or data.get('code') or data.get('name') or "Unknown"
        logger.info(f"Agent processing: {name}")
        result = run_download(name)
        output = {"jurisdiction": data, "name": name, "success": result["success"], "timestamp": datetime.now().isoformat()}
        print(json.dumps(output))
        sys.exit(0 if result["success"] else 1)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        sys.exit(1)
