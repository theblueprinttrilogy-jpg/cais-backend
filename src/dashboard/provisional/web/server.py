#!/usr/bin/env python3
"""
Servidor Web del Dashboard Provisional CAIS
Accesible en http://localhost:8080
"""

import json
import os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import webbrowser

# Importar módulos del sistema
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.worm.worm_ledger import WormLedger

class CAISWebHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para el dashboard web."""
    
    def __init__(self, *args, **kwargs):
        self.worm = WormLedger()
        self.ideas_file = Path("~/PROMETHEUS/data/ideas.json").expanduser()
        self.feedback_file = Path("~/PROMETHEUS/data/feedback.json").expanduser()
        self.ideas = self._load_ideas()
        self.feedback = self._load_feedback()
        super().__init__(*args, **kwargs)
    
    def _load_ideas(self) -> list:
        if self.ideas_file.exists():
            with open(self.ideas_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_ideas(self):
        with open(self.ideas_file, 'w') as f:
            json.dump(self.ideas, f, indent=2, default=str)
    
    def _load_feedback(self) -> list:
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_feedback(self):
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback, f, indent=2, default=str)
    
    def do_GET(self):
        """Manejar peticiones GET."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self._serve_html()
        elif path == '/api/status':
            self._serve_status()
        elif path == '/api/ideas':
            self._serve_ideas()
        elif path == '/api/feedback':
            self._serve_feedback()
        elif path == '/api/worm':
            self._serve_worm()
        elif path.startswith('/static/'):
            self._serve_static(path)
        else:
            self._send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        """Manejar peticiones POST."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        if path == '/api/idea':
            self._add_idea(data)
        elif path == '/api/feedback':
            self._add_feedback(data)
        elif path == '/api/improvement':
            self._add_improvement(data)
        else:
            self._send_json({'error': 'Not found'}, 404)
    
    def _serve_html(self):
        """Servir el HTML principal."""
        html = self._get_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _serve_status(self):
        """Servir estado del sistema."""
        status = self._get_system_status()
        self._send_json(status)
    
    def _serve_ideas(self):
        """Servir ideas registradas."""
        self._send_json({'ideas': self.ideas})
    
    def _serve_feedback(self):
        """Servir feedback registrado."""
        self._send_json({'feedback': self.feedback})
    
    def _serve_worm(self):
        """Servir entradas del WORM."""
        entries = self.worm.get_entries(limit=20)
        self._send_json({'entries': entries})
    
    def _serve_static(self, path):
        """Servir archivos estáticos."""
        filename = path.replace('/static/', '')
        filepath = Path(__file__).parent / 'static' / filename
        
        if filepath.exists():
            self.send_response(200)
            if filename.endswith('.css'):
                self.send_header('Content-type', 'text/css')
            elif filename.endswith('.js'):
                self.send_header('Content-type', 'application/javascript')
            elif filename.endswith('.png'):
                self.send_header('Content-type', 'image/png')
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self._send_json({'error': 'File not found'}, 404)
    
    def _send_json(self, data, status=200):
        """Enviar respuesta JSON."""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))
    
    def _add_idea(self, data):
        """Agregar una idea."""
        idea = {
            'id': f"IDEA-{len(self.ideas)+1:04d}",
            'title': data.get('title', 'Sin título'),
            'description': data.get('description', ''),
            'category': data.get('category', 'funcionalidad'),
            'priority': data.get('priority', 'media'),
            'status': 'registrada',
            'created_at': datetime.now().isoformat(),
            'source': 'web'
        }
        self.ideas.append(idea)
        self._save_ideas()
        self.worm.append_entry('IDEA_REGISTRADA', idea, 'web')
        self._send_json({'success': True, 'idea': idea})
    
    def _add_feedback(self, data):
        """Agregar feedback."""
        feedback = {
            'id': f"FB-{len(self.feedback)+1:04d}",
            'topic': data.get('topic', 'General'),
            'rating': int(data.get('rating', 5)),
            'comment': data.get('comment', ''),
            'created_at': datetime.now().isoformat(),
            'source': 'web'
        }
        self.feedback.append(feedback)
        self._save_feedback()
        self.worm.append_entry('FEEDBACK_REGISTRADO', feedback, 'web')
        self._send_json({'success': True, 'feedback': feedback})
    
    def _add_improvement(self, data):
        """Agregar mejora."""
        improvement = {
            'id': f"IMP-{len(self.ideas)+1:04d}",
            'type': data.get('type', 'nueva_funcionalidad'),
            'title': data.get('title', 'Sin título'),
            'description': data.get('description', ''),
            'benefit': data.get('benefit', ''),
            'complexity': data.get('complexity', 'media'),
            'status': 'sugerida',
            'created_at': datetime.now().isoformat(),
            'source': 'web'
        }
        self.ideas.append(improvement)
        self._save_ideas()
        self.worm.append_entry('MEJORA_SUGERIDA', improvement, 'web')
        self._send_json({'success': True, 'improvement': improvement})
    
    def _get_system_status(self) -> dict:
        """Obtener estado del sistema."""
        return {
            'constitution': self._check_constitution(),
            'laws': self._check_laws(),
            'generated': self._check_generated(),
            'agents': self._check_agents(),
            'worm': self._check_worm(),
            'ideas': len(self.ideas),
            'feedback': len(self.feedback)
        }
    
    def _check_constitution(self) -> dict:
        path = Path("~/PROMETHEUS/input/constitution").expanduser()
        if path.exists():
            files = list(path.glob("*.pdf"))
            return {'ok': True, 'count': len(files)}
        return {'ok': False, 'count': 0}
    
    def _check_laws(self) -> dict:
        path = Path("~/PROMETHEUS/input/laws").expanduser()
        if path.exists():
            files = list(path.glob("*.pdf"))
            return {'ok': True, 'count': len(files)}
        return {'ok': False, 'count': 0}
    
    def _check_generated(self) -> dict:
        path = Path("~/PROMETHEUS/output/generated_code").expanduser()
        if path.exists():
            files = list(path.glob("*.py"))
            return {'ok': True, 'count': len(files)}
        return {'ok': False, 'count': 0}
    
    def _check_agents(self) -> int:
        path = Path("~/PROMETHEUS/output/generated_code/agents").expanduser()
        if path.exists():
            return len(list(path.glob("*.py")))
        return 0
    
    def _check_worm(self) -> dict:
        try:
            status = self.worm.get_status()
            return {'ok': True, 'entries': status['total_entries'], 'integrity': status['integrity']}
        except:
            return {'ok': False, 'entries': 0}
    
    def _get_html(self) -> str:
        """Generar HTML del dashboard."""
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 CAIS - Dashboard Provisional</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0A1628;
            color: #F0F4F8;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #0A1628 0%, #1A2A4A 100%);
            padding: 30px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(135deg, #D4A84A, #F5D06A);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p { color: #8A9AB0; margin-top: 10px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(26, 42, 74, 0.8);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
        }
        .card h3 {
            font-size: 14px;
            text-transform: uppercase;
            color: #8A9AB0;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .card .value {
            font-size: 2em;
            font-weight: 700;
            color: #F0F4F8;
        }
        .card .status-ok { color: #00D4AA; }
        .card .status-error { color: #FF6B6B; }
        .form-section {
            background: rgba(26, 42, 74, 0.8);
            border-radius: 12px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 30px;
        }
        .form-section h2 {
            color: #D4A84A;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            color: #8A9AB0;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 10px 15px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #F0F4F8;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #D4A84A;
        }
        .form-group textarea { min-height: 100px; resize: vertical; }
        .btn {
            padding: 10px 25px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #D4A84A, #F5D06A);
            color: #0A1628;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(212, 168, 74, 0.3); }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #F0F4F8;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.2); }
        .btn-danger {
            background: #FF6B6B;
            color: #0A1628;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .table th {
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            color: #8A9AB0;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }
        .table td {
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.03);
        }
        .table tr:hover td { background: rgba(255,255,255,0.02); }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-alta { background: #FF6B6B; color: #0A1628; }
        .badge-media { background: #F5A623; color: #0A1628; }
        .badge-baja { background: #00D4AA; color: #0A1628; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 8px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid transparent;
        }
        .tab:hover { background: rgba(255,255,255,0.1); }
        .tab.active {
            background: rgba(212, 168, 74, 0.2);
            border-color: #D4A84A;
            color: #D4A84A;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .notification {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            display: none;
        }
        .notification.success {
            display: block;
            background: rgba(0, 212, 170, 0.1);
            border: 1px solid #00D4AA;
            color: #00D4AA;
        }
        .notification.error {
            display: block;
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid #FF6B6B;
            color: #FF6B6B;
        }
        .footer {
            text-align: center;
            color: #8A9AB0;
            font-size: 12px;
            padding: 20px 0;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.1);
            border-top: 2px solid #D4A84A;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .worm-chain {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            padding: 10px 0;
        }
        .worm-block {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.05);
            border-radius: 6px;
            font-size: 12px;
            color: #8A9AB0;
            border: 2px solid rgba(255,255,255,0.1);
        }
        .worm-block.active {
            border-color: #00D4AA;
            background: rgba(0, 212, 170, 0.1);
            color: #00D4AA;
        }
        .worm-arrow { color: #8A9AB0; }
        @media (max-width: 768px) {
            .header h1 { font-size: 1.8em; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🧠 CAIS - Dashboard Provisional</h1>
            <p>Interacción y Feedback para el Soberano</p>
            <p style="font-size:12px;color:#666;margin-top:10px;">
                🔗 <span id="status-indicator">Conectado</span>
            </p>
        </div>

        <!-- Notifications -->
        <div id="notification" class="notification"></div>

        <!-- Status Cards -->
        <div class="grid" id="status-cards">
            <div class="card">
                <h3>📄 Constitución</h3>
                <div class="value" id="status-constitution">--</div>
            </div>
            <div class="card">
                <h3>📜 Leyes</h3>
                <div class="value" id="status-laws">--</div>
            </div>
            <div class="card">
                <h3>💻 Código Generado</h3>
                <div class="value" id="status-generated">--</div>
            </div>
            <div class="card">
                <h3>🧠 Agentes</h3>
                <div class="value" id="status-agents">--</div>
            </div>
            <div class="card">
                <h3>🔗 WORM</h3>
                <div class="value" id="status-worm">--</div>
            </div>
            <div class="card">
                <h3>💡 Ideas</h3>
                <div class="value" id="status-ideas">--</div>
            </div>
            <div class="card">
                <h3>📝 Feedback</h3>
                <div class="value" id="status-feedback">--</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
            <div class="tab active" data-tab="ideas">💡 Ideas</div>
            <div class="tab" data-tab="feedback">📝 Feedback</div>
            <div class="tab" data-tab="worm">🔗 WORM</div>
            <div class="tab" data-tab="new-idea">➕ Nueva Idea</div>
            <div class="tab" data-tab="new-feedback">📝 Nuevo Feedback</div>
        </div>

        <!-- Tab: Ideas -->
        <div id="tab-ideas" class="tab-content active">
            <div class="form-section">
                <h2>💡 Ideas Registradas</h2>
                <div id="ideas-list">
                    <p style="color:#8A9AB0;">Cargando ideas...</p>
                </div>
            </div>
        </div>

        <!-- Tab: Feedback -->
        <div id="tab-feedback" class="tab-content">
            <div class="form-section">
                <h2>📝 Feedback Registrado</h2>
                <div id="feedback-list">
                    <p style="color:#8A9AB0;">Cargando feedback...</p>
                </div>
            </div>
        </div>

        <!-- Tab: WORM -->
        <div id="tab-worm" class="tab-content">
            <div class="form-section">
                <h2>🔗 WORM Ledger</h2>
                <div id="worm-entries">
                    <p style="color:#8A9AB0;">Cargando entradas WORM...</p>
                </div>
            </div>
        </div>

        <!-- Tab: Nueva Idea -->
        <div id="tab-new-idea" class="tab-content">
            <div class="form-section">
                <h2>💡 Registrar Nueva Idea</h2>
                <form id="idea-form">
                    <div class="form-group">
                        <label>Título</label>
                        <input type="text" id="idea-title" required placeholder="Título de la idea">
                    </div>
                    <div class="form-group">
                        <label>Descripción</label>
                        <textarea id="idea-description" required placeholder="Describe tu idea..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Categoría</label>
                        <select id="idea-category">
                            <option value="arquitectura">Arquitectura</option>
                            <option value="funcionalidad" selected>Funcionalidad</option>
                            <option value="seguridad">Seguridad</option>
                            <option value="UX">UX</option>
                            <option value="rendimiento">Rendimiento</option>
                            <option value="otro">Otro</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Prioridad</label>
                        <select id="idea-priority">
                            <option value="alta">Alta</option>
                            <option value="media" selected>Media</option>
                            <option value="baja">Baja</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary">Registrar Idea</button>
                </form>
            </div>
        </div>

        <!-- Tab: Nuevo Feedback -->
        <div id="tab-new-feedback" class="tab-content">
            <div class="form-section">
                <h2>📝 Registrar Feedback</h2>
                <form id="feedback-form">
                    <div class="form-group">
                        <label>Tópico</label>
                        <input type="text" id="feedback-topic" required placeholder="¿Sobre qué quieres dar feedback?">
                    </div>
                    <div class="form-group">
                        <label>Calificación (1-10)</label>
                        <input type="number" id="feedback-rating" min="1" max="10" value="5" required>
                    </div>
                    <div class="form-group">
                        <label>Comentario</label>
                        <textarea id="feedback-comment" required placeholder="Tu comentario..."></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Enviar Feedback</button>
                </form>
            </div>
        </div>

        <div class="footer">
            🧠 CAIS System v1.0 | Dashboard Provisional | 
            <span id="timestamp"></span>
        </div>
    </div>

    <script>
        // Estado global
        let ideas = [];
        let feedback = [];
        let wormEntries = [];

        // Mostrar notificación
        function showNotification(message, type = 'success') {
            const el = document.getElementById('notification');
            el.textContent = message;
            el.className = `notification ${type}`;
            setTimeout(() => { el.className = 'notification'; }, 5000);
        }

        // Cargar estado
        async function loadStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('status-constitution').textContent = 
                    data.constitution.ok ? `✅ ${data.constitution.count} PDFs` : '⚠️ No hay';
                document.getElementById('status-laws').textContent = 
                    data.laws.ok ? `✅ ${data.laws.count} PDFs` : '⚠️ No hay';
                document.getElementById('status-generated').textContent = 
                    data.generated.ok ? `✅ ${data.generated.count} archivos` : '⚠️ No hay';
                document.getElementById('status-agents').textContent = 
                    data.agents > 0 ? `✅ ${data.agents} agentes` : '⚠️ No hay';
                document.getElementById('status-worm').textContent = 
                    data.worm.ok ? `✅ ${data.worm.entries} entradas` : '⚠️ Error';
                document.getElementById('status-ideas').textContent = 
                    data.ideas > 0 ? `✅ ${data.ideas}` : '0';
                document.getElementById('status-feedback').textContent = 
                    data.feedback > 0 ? `✅ ${data.feedback}` : '0';
                
                document.getElementById('status-indicator').textContent = '✅ Conectado';
                document.getElementById('status-indicator').style.color = '#00D4AA';
            } catch (e) {
                document.getElementById('status-indicator').textContent = '❌ Desconectado';
                document.getElementById('status-indicator').style.color = '#FF6B6B';
                console.error('Error loading status:', e);
            }
        }

        // Cargar ideas
        async function loadIdeas() {
            try {
                const res = await fetch('/api/ideas');
                const data = await res.json();
                ideas = data.ideas || [];
                renderIdeas();
            } catch (e) {
                console.error('Error loading ideas:', e);
            }
        }

        function renderIdeas() {
            const container = document.getElementById('ideas-list');
            if (ideas.length === 0) {
                container.innerHTML = '<p style="color:#8A9AB0;">No hay ideas registradas aún.</p>';
                return;
            }
            
            let html = `<table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Título</th>
                        <th>Categoría</th>
                        <th>Prioridad</th>
                        <th>Estado</th>
                        <th>Fecha</th>
                    </tr>
                </thead>
                <tbody>`;
            
            ideas.slice().reverse().forEach(idea => {
                const priorityClass = idea.priority === 'alta' ? 'badge-alta' : 
                                     idea.priority === 'media' ? 'badge-media' : 'badge-baja';
                html += `<tr>
                    <td><strong>${idea.id}</strong></td>
                    <td>${idea.title}</td>
                    <td>${idea.category}</td>
                    <td><span class="badge ${priorityClass}">${idea.priority}</span></td>
                    <td>${idea.status}</td>
                    <td style="font-size:12px;color:#666;">${idea.created_at ? idea.created_at.slice(0,16) : ''}</td>
                </tr>`;
            });
            
            html += `</tbody></table>`;
            container.innerHTML = html;
        }

        // Cargar feedback
        async function loadFeedback() {
            try {
                const res = await fetch('/api/feedback');
                const data = await res.json();
                feedback = data.feedback || [];
                renderFeedback();
            } catch (e) {
                console.error('Error loading feedback:', e);
            }
        }

        function renderFeedback() {
            const container = document.getElementById('feedback-list');
            if (feedback.length === 0) {
                container.innerHTML = '<p style="color:#8A9AB0;">No hay feedback registrado aún.</p>';
                return;
            }
            
            let html = `<table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Tópico</th>
                        <th>Rating</th>
                        <th>Comentario</th>
                        <th>Fecha</th>
                    </tr>
                </thead>
                <tbody>`;
            
            feedback.slice().reverse().forEach(fb => {
                const stars = '⭐'.repeat(Math.round(fb.rating / 2));
                html += `<tr>
                    <td><strong>${fb.id}</strong></td>
                    <td>${fb.topic}</td>
                    <td>${stars} ${fb.rating}/10</td>
                    <td>${fb.comment}</td>
                    <td style="font-size:12px;color:#666;">${fb.created_at ? fb.created_at.slice(0,16) : ''}</td>
                </tr>`;
            });
            
            html += `</tbody></table>`;
            container.innerHTML = html;
        }

        // Cargar WORM
        async function loadWorm() {
            try {
                const res = await fetch('/api/worm');
                const data = await res.json();
                wormEntries = data.entries || [];
                renderWorm();
            } catch (e) {
                console.error('Error loading worm:', e);
            }
        }

        function renderWorm() {
            const container = document.getElementById('worm-entries');
            if (wormEntries.length === 0) {
                container.innerHTML = '<p style="color:#8A9AB0;">No hay entradas en el WORM.</p>';
                return;
            }
            
            let html = `<div style="overflow-x:auto;">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Secuencia</th>
                            <th>Evento</th>
                            <th>Actor</th>
                            <th>Hash</th>
                            <th>Fecha</th>
                        </tr>
                    </thead>
                    <tbody>`;
            
            wormEntries.slice().reverse().forEach(entry => {
                html += `<tr>
                    <td>${entry.sequence || '?'}</td>
                    <td>${entry.event_type || '?'}</td>
                    <td>${entry.actor || '?'}</td>
                    <td style="font-family:monospace;font-size:11px;color:#666;">${entry.hash ? entry.hash.slice(0,16)+'...' : ''}</td>
                    <td style="font-size:12px;color:#666;">${entry.timestamp ? entry.timestamp.slice(0,16) : ''}</td>
                </tr>`;
            });
            
            html += `</tbody></table></div>`;
            container.innerHTML = html;
        }

        // Tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                const tabId = this.dataset.tab;
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                document.getElementById(`tab-${tabId}`).classList.add('active');
            });
        });

        // Form: Nueva Idea
        document.getElementById('idea-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const data = {
                title: document.getElementById('idea-title').value,
                description: document.getElementById('idea-description').value,
                category: document.getElementById('idea-category').value,
                priority: document.getElementById('idea-priority').value
            };
            
            try {
                const res = await fetch('/api/idea', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('✅ Idea registrada exitosamente!');
                    this.reset();
                    loadIdeas();
                    loadStatus();
                } else {
                    showNotification('❌ Error al registrar idea', 'error');
                }
            } catch (e) {
                showNotification('❌ Error de conexión', 'error');
            }
        });

        // Form: Nuevo Feedback
        document.getElementById('feedback-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const data = {
                topic: document.getElementById('feedback-topic').value,
                rating: parseInt(document.getElementById('feedback-rating').value),
                comment: document.getElementById('feedback-comment').value
            };
            
            try {
                const res = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('✅ Feedback registrado exitosamente!');
                    this.reset();
                    loadFeedback();
                    loadStatus();
                } else {
                    showNotification('❌ Error al registrar feedback', 'error');
                }
            } catch (e) {
                showNotification('❌ Error de conexión', 'error');
            }
        });

        // Actualizar timestamp
        function updateTimestamp() {
            document.getElementById('timestamp').textContent = new Date().toLocaleString();
        }

        // Cargar todo
        async function loadAll() {
            await loadStatus();
            await loadIdeas();
            await loadFeedback();
            await loadWorm();
            updateTimestamp();
        }

        // Recargar cada 30 segundos
        loadAll();
        setInterval(() => {
            loadStatus();
            updateTimestamp();
        }, 30000);
    </script>
</body>
</html>
        """

    def log_message(self, format, *args):
        """Suprimir logs del servidor."""
        pass


def run_server(port: int = 8080):
    """Ejecutar el servidor web."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CAISWebHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🌐 CAIS Dashboard Web                                     ║
║                                                              ║
║   Servidor ejecutándose en:                                 ║
║   http://localhost:{port}                                    ║
║                                                              ║
║   Presiona Ctrl+C para detener el servidor                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Abrir en el navegador
    webbrowser.open(f'http://localhost:{port}')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")


if __name__ == "__main__":
    run_server()
