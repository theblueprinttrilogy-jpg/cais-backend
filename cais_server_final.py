#!/usr/bin/env python3
"""
Servidor CAIS Multilingüe - 20 Idiomas con Diccionarios de Construcción
"""

import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from typing import Dict, List, Optional

class CAISMultilingualHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        print(f"📥 GET: {path}")  # Debug
        
        if path == '/':
            self._serve_html()
        elif path == '/api/status':
            self._serve_status()
        elif path == '/api/translate':
            self._serve_translate(parsed.query)
        else:
            self._send_json({'error': 'Not found', 'path': path}, 404)
    
    def _serve_html(self):
        try:
            with open('index.html', 'r') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except FileNotFoundError:
            self._send_json({'error': 'index.html not found'}, 404)
    
    def _serve_status(self):
        """Servir estado del sistema."""
        status = {
            'constitution': 4,
            'laws': 6,
            'generated': 2,
            'agents': 3,
            'worm': 1,
            'ideas': 0,
            'totalSections': '100',
            'totalRules': 4,
            'totalKeywords': '15'
        }
        self._send_json(status)
    
    def _serve_translate(self, query: str):
        """Traducir término de construcción."""
        params = urllib.parse.parse_qs(query)
        term = params.get('term', [''])[0]
        from_lang = params.get('from', ['en'])[0]
        to_lang = params.get('to', ['es'])[0]
        
        if not term:
            self._send_json({'error': 'No term provided'}, 400)
            return
        
        # Buscar en diccionarios
        result = self._translate_term(term, from_lang, to_lang)
        self._send_json(result)
    
    def _translate_term(self, term: str, from_lang: str, to_lang: str) -> Dict:
        """Traducir un término usando los diccionarios."""
        if from_lang == to_lang:
            return {'original': term, 'translated': term, 'from': from_lang, 'to': to_lang}
        
        dict_dir = Path("src/dashboard/provisional/web/dictionaries")
        result = {'original': term, 'from': from_lang, 'to': to_lang, 'translated': term}
        
        # Cargar diccionario de origen
        from_file = dict_dir / from_lang / "construction_terms.json"
        to_file = dict_dir / to_lang / "construction_terms.json"
        
        if from_file.exists():
            try:
                with open(from_file, 'r', encoding='utf-8') as f:
                    from_dict = json.load(f)
                
                # Buscar término en el diccionario de origen
                for category, terms in from_dict.items():
                    if category == 'meta':
                        continue
                    if term in terms:
                        # Encontrado - buscar en diccionario destino
                        if to_file.exists():
                            with open(to_file, 'r', encoding='utf-8') as f:
                                to_dict = json.load(f)
                            if category in to_dict and term in to_dict[category]:
                                result['translated'] = to_dict[category][term]
                                return result
                        # Si no está en destino, devolver el término original
                        return result
            except Exception as e:
                result['error'] = str(e)
                return result
        
        # Si no se encuentra en el diccionario, devolver el término original
        return result
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

def main():
    port = 8080
    server = HTTPServer(('', port), CAISMultilingualHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║   🌐 CAIS Dashboard Multilingüe                             ║
║   http://localhost:{port}                                    ║
║   🌍 20 Idiomas - Diccionarios de Construcción             ║
║   Presiona Ctrl+C para detener                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")

if __name__ == "__main__":
    main()
