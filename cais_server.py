#!/usr/bin/env python3
"""
Servidor CAIS con API de estado
"""

import json
import os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

class CAISHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/':
            self._serve_html()
        elif path == '/api/status':
            self._serve_status()
        else:
            self._send_json({'error': 'Not found'}, 404)
    
    def _serve_html(self):
        with open('index.html', 'r') as f:
            html = f.read()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _serve_status(self):
        """Servir estado del sistema en JSON"""
        # Contar archivos
        constitution = len(list(Path("~/PROMETHEUS/input/constitution").expanduser().glob("*.pdf")))
        laws = len(list(Path("~/PROMETHEUS/input/laws").expanduser().glob("*.pdf")))
        generated = len(list(Path("~/PROMETHEUS/output/generated_code").expanduser().glob("*.py")))
        agents = len(list(Path("~/PROMETHEUS/output/generated_code/agents").expanduser().glob("*.py")))
        
        # Contar ideas
        ideas_file = Path("~/PROMETHEUS/data/ideas.json").expanduser()
        ideas = 0
        if ideas_file.exists():
            with open(ideas_file, 'r') as f:
                ideas = len(json.load(f))
        
        # Estado WORM
        worm_entries = 0
        try:
            from src.worm.worm_ledger import WormLedger
            worm = WormLedger()
            status = worm.get_status()
            worm_entries = status.get('total_entries', 0)
        except:
            worm_entries = 0
        
        # Reglas y keywords
        rules_dir = Path("~/PROMETHEUS/output/generated_rules").expanduser()
        rules = 0
        keywords = 0
        if rules_dir.exists():
            rules = len(list(rules_dir.glob("*.json")))
        
        status = {
            'constitution': constitution,
            'laws': laws,
            'generated': generated,
            'agents': agents,
            'worm': worm_entries,
            'ideas': ideas,
            'totalSections': '100',
            'totalRules': rules,
            'totalKeywords': '15'
        }
        self._send_json(status)
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Silenciar logs

def main():
    port = 8080
    server = HTTPServer(('', port), CAISHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║   🌐 CAIS Dashboard Web                                     ║
║   http://localhost:{port}                                    ║
║   Presiona Ctrl+C para detener                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")

if __name__ == "__main__":
    main()
