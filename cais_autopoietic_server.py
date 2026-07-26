#!/usr/bin/env python3
"""
CAIS - Sistema Autopoiético Completo
1. Seleccionar TODOS los archivos
2. Descargar
3. Comprimir
4. Extraer conocimiento
5. Auto-crear
"""

import os
import json
import zipfile
import hashlib
import re
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from src.integrations.gdrive_explorer import GDriveExplorer
from src.core.logging_config import ForensicLogger
from src.worm.worm_ledger import WormLedger

app = FastAPI(title="CAIS - Autopoietic System")

# Directorios
DOWNLOAD_DIR = Path("./downloads")
COMPRESSED_DIR = Path("./compressed")
PROCESSED_DIR = Path("./processed")
KNOWLEDGE_DIR = Path("./knowledge")
CONFIG_DIR = Path("./config")
CODE_DIR = Path("./generated_code")

for d in [DOWNLOAD_DIR, COMPRESSED_DIR, PROCESSED_DIR, KNOWLEDGE_DIR, CONFIG_DIR, CODE_DIR]:
    d.mkdir(exist_ok=True)

logger = ForensicLogger()
worm = WormLedger()

# Archivos de estado
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "knowledge_base.json"
CONFIG_FILE = CONFIG_DIR / "cais_config.json"

def get_all_files():
    """Obtiene TODOS los archivos de Google Drive"""
    explorer = GDriveExplorer()
    all_files = []
    page_token = None
    
    while True:
        try:
            response = explorer.service.files().list(
                q="trashed=false",
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                pageToken=page_token
            ).execute()
            
            files = response.get('files', [])
            all_files.extend(files)
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            print(f"Error: {e}")
            break
    
    return all_files

def download_file(file_id, file_name):
    """Descarga un archivo de Google Drive"""
    try:
        explorer = GDriveExplorer()
        
        # Verificar si es un Google Doc
        file_meta = explorer.service.files().get(
            fileId=file_id,
            fields='mimeType'
        ).execute()
        
        mime_type = file_meta.get('mimeType', '')
        output_path = DOWNLOAD_DIR / file_name
        
        if mime_type == 'application/vnd.google-apps.document':
            # Exportar como PDF
            request = explorer.service.files().export_media(
                fileId=file_id,
                mimeType='application/pdf'
            )
            output_path = DOWNLOAD_DIR / f"{file_name}.pdf"
            with open(output_path, 'wb') as f:
                request.execute(f)
            return str(output_path), "pdf"
        else:
            # Descargar normalmente
            request = explorer.service.files().get_media(fileId=file_id)
            with open(output_path, 'wb') as f:
                request.execute(f)
            return str(output_path), "unknown"
            
    except Exception as e:
        print(f"Error descargando {file_name}: {e}")
        return None, None

def extract_text_from_file(file_path):
    """Extrae texto de un archivo según su extensión"""
    try:
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        
        elif ext in ['.txt', '.md', '.csv', '.json', '.xml', '.py', '.js']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif ext in ['.docx', '.doc']:
            # Intentar leer con python-docx (si está instalado)
            try:
                import docx
                doc = docx.Document(file_path)
                return '\n'.join([p.text for p in doc.paragraphs])
            except:
                return ""
        
        else:
            return ""
            
    except Exception as e:
        return f"[Error: {e}]"

def analyze_content(text, filename):
    """Analiza el contenido y extrae patrones"""
    patterns = []
    keywords = []
    
    # Palabras clave de construcción
    construction_keywords = [
        'construction', 'building', 'structural', 'foundation', 'concrete',
        'steel', 'wood', 'framing', 'roofing', 'plumbing', 'electrical',
        'hvac', 'mechanical', 'architect', 'engineer', 'contractor',
        'project', 'permit', 'inspection', 'code', 'compliance',
        'safety', 'quality', 'schedule', 'budget', 'cais',
        'blueprint', 'plan', 'specification', 'material', 'labor'
    ]
    
    text_lower = text.lower()
    for keyword in construction_keywords:
        if keyword in text_lower:
            keywords.append(keyword)
    
    # Patrones de código
    code_patterns = [
        (r'def\s+(\w+)\s*\(', 'function'),
        (r'class\s+(\w+)', 'class'),
        (r'import\s+(\w+)', 'import'),
        (r'async\s+def\s+(\w+)', 'async_function'),
    ]
    
    for pattern, ptype in code_patterns:
        matches = re.findall(pattern, text)
        if matches:
            patterns.append({
                "type": ptype,
                "pattern": pattern,
                "matches": matches[:10]
            })
    
    return {
        "patterns": patterns,
        "keywords": list(set(keywords)),
        "word_count": len(text.split()),
        "char_count": len(text)
    }

def process_archives():
    """Procesa todos los archivos descargados y extrae conocimiento"""
    knowledge = load_knowledge()
    config = load_config()
    
    files = list(DOWNLOAD_DIR.glob("*"))
    if not files:
        return {"success": False, "error": "No hay archivos para procesar"}
    
    # Crear ZIP
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"CAIS_Data_{timestamp}.zip"
    zip_path = COMPRESSED_DIR / zip_name
    
    all_keywords = []
    all_patterns = []
    files_processed = 0
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            if file_path.is_file():
                zipf.write(file_path, file_path.name)
                
                # Extraer texto
                text = extract_text_from_file(file_path)
                if text and len(text) > 50:
                    analysis = analyze_content(text, file_path.name)
                    all_keywords.extend(analysis.get('keywords', []))
                    all_patterns.extend(analysis.get('patterns', []))
                    files_processed += 1
    
    # Actualizar conocimiento
    if all_keywords:
        knowledge["keywords"] = list(set(knowledge.get("keywords", []) + all_keywords))
    
    if all_patterns:
        knowledge["patterns"] = knowledge.get("patterns", []) + all_patterns
    
    entry = {
        "id": hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
        "source": str(zip_path),
        "processed_at": datetime.now().isoformat(),
        "files_count": files_processed,
        "keywords": list(set(all_keywords)),
        "patterns": all_patterns,
        "total_keywords": len(set(all_keywords)),
        "total_patterns": len(all_patterns)
    }
    
    knowledge["entries"] = knowledge.get("entries", []) + [entry]
    knowledge["total_files_processed"] = knowledge.get("total_files_processed", 0) + files_processed
    knowledge["last_update"] = datetime.now().isoformat()
    
    save_knowledge(knowledge)
    
    # Actualizar configuración
    config["knowledge_entries"] = len(knowledge["entries"])
    config["last_update"] = datetime.now().isoformat()
    config["keywords_count"] = len(knowledge.get("keywords", []))
    save_config(config)
    
    # Registrar en WORM
    worm.append_entry(
        event_type="KNOWLEDGE_EXTRACTED",
        payload={
            "source": str(zip_path),
            "files": files_processed,
            "keywords": len(set(all_keywords)),
            "patterns": len(all_patterns)
        },
        actor="system"
    )
    
    return {
        "success": True,
        "zip_path": str(zip_path),
        "files_processed": files_processed,
        "keywords_found": len(set(all_keywords)),
        "patterns_found": len(all_patterns),
        "knowledge_entries": len(knowledge["entries"])
    }

def self_create():
    """Auto-creación: genera código y reglas desde el conocimiento"""
    knowledge = load_knowledge()
    config = load_config()
    
    modules_generated = 0
    rules_created = 0
    
    # Generar módulo desde patrones
    if knowledge.get("patterns"):
        code = generate_module(knowledge["patterns"])
        if code:
            module_path = CODE_DIR / f"auto_module_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            with open(module_path, 'w') as f:
                f.write(code)
            modules_generated += 1
    
    # Generar reglas desde keywords
    if knowledge.get("keywords"):
        rules = generate_rules(knowledge["keywords"])
        if rules:
            rules_path = CONFIG_DIR / "generated_rules.json"
            with open(rules_path, 'w') as f:
                json.dump(rules, f, indent=2)
            rules_created = len(rules)
    
    # Actualizar configuración
    config["modules_generated"] = config.get("modules_generated", 0) + modules_generated
    config["rules_count"] = config.get("rules_count", 0) + rules_created
    config["self_creation_cycles"] = config.get("self_creation_cycles", 0) + 1
    config["last_self_create"] = datetime.now().isoformat()
    save_config(config)
    
    worm.append_entry(
        event_type="SELF_CREATION",
        payload={
            "modules_generated": modules_generated,
            "rules_created": rules_created,
            "cycle": config["self_creation_cycles"]
        },
        actor="system"
    )
    
    return {
        "success": True,
        "modules_generated": modules_generated,
        "rules_created": rules_created,
        "cycles": config["self_creation_cycles"]
    }

def generate_module(patterns):
    """Genera un módulo Python desde patrones"""
    functions = []
    imports = set()
    
    for p in patterns:
        if p.get('type') == 'function':
            for match in p.get('matches', []):
                functions.append(f"    def {match}(self, *args, **kwargs):\n        pass")
        elif p.get('type') == 'import':
            for match in p.get('matches', []):
                imports.add(match)
    
    if not functions:
        return None
    
    import_lines = "\n".join([f"import {i}" for i in imports if i])
    
    code = f'''"""
Módulo auto-generado por CAIS
Fecha: {datetime.now().isoformat()}
Basado en patrones encontrados en documentos
Ciclo de auto-creación: {load_config().get("self_creation_cycles", 0) + 1}
"""

{import_lines}

class AutoModule:
    """Módulo generado automáticamente"""
    
    def __init__(self):
        self.name = "AutoModule"
        self.version = "1.0.0"
        self.generated_at = "{datetime.now().isoformat()}"
        self.cycle = {load_config().get("self_creation_cycles", 0) + 1}
    
{chr(10).join(functions)}

    def info(self):
        return {{
            "name": self.name,
            "version": self.version,
            "generated_at": self.generated_at,
            "cycle": self.cycle,
            "functions": {len(functions)}
        }}
'''
    return code

def generate_rules(keywords):
    """Genera reglas desde keywords"""
    rules = []
    for keyword in keywords[:50]:
        rules.append({
            "id": f"RULE_{keyword.upper()[:20]}",
            "keyword": keyword,
            "description": f"Regla generada automáticamente para '{keyword}'",
            "priority": "medium" if len(keyword) > 5 else "low",
            "generated_at": datetime.now().isoformat()
        })
    return rules

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    config = {
        "system_name": "CAIS - Autopoietic System",
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "knowledge_entries": 0,
        "self_creation_cycles": 0,
        "modules_generated": 0,
        "rules_count": 0,
        "keywords_count": 0
    }
    save_config(config)
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_knowledge():
    if KNOWLEDGE_FILE.exists():
        with open(KNOWLEDGE_FILE, 'r') as f:
            return json.load(f)
    return {"entries": [], "keywords": [], "patterns": [], "total_files_processed": 0}

def save_knowledge(knowledge):
    with open(KNOWLEDGE_FILE, 'w') as f:
        json.dump(knowledge, f, indent=2)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAIS - Autopoietic System</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0a1a; color: #e0e0e0; min-height: 100vh; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #00d4ff; font-size: 2.5rem; text-align: center; }
            .subtitle { text-align: center; color: #666688; margin-bottom: 30px; }
            
            .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
            .card { background: #141425; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; text-align: center; }
            .card .value { font-size: 2.5rem; font-weight: bold; color: #00d4ff; }
            .card .label { color: #666688; font-size: 0.8rem; margin-top: 5px; }
            
            .btn {
                padding: 16px 40px; border: none; border-radius: 30px;
                font-weight: 700; font-size: 1.2rem; cursor: pointer;
                transition: all 0.3s; display: inline-block;
            }
            .btn:hover { transform: scale(1.05); box-shadow: 0 0 30px rgba(0,212,255,0.2); }
            .btn-primary { background: #00d4ff; color: #0a0a1a; }
            .btn-success { background: #00ff88; color: #0a0a1a; }
            .btn-warning { background: #ff8844; color: #0a0a1a; }
            .btn-danger { background: #ff4466; color: white; }
            
            .actions { display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; margin-bottom: 30px; }
            
            .progress-container {
                background: #141425; border-radius: 12px; padding: 20px;
                border: 1px solid #2a2a4a; margin-bottom: 20px; display: none;
            }
            .progress-bar { height: 8px; background: #2a2a5a; border-radius: 4px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff88); width: 0%; transition: width 0.5s; }
            .progress-text { text-align: center; margin-top: 10px; color: #8888aa; }
            
            .log-container {
                background: #0a0a1a; border-radius: 12px; padding: 15px;
                border: 1px solid #1a1a3a; max-height: 300px; overflow-y: auto;
                font-family: monospace; font-size: 0.85rem; display: none;
            }
            .log-line { padding: 3px 0; border-bottom: 1px solid #0a0a1a; }
            .log-line .time { color: #444466; margin-right: 10px; }
            .log-line .success { color: #00ff88; }
            .log-line .info { color: #00d4ff; }
            .log-line .warning { color: #ff8844; }
            .log-line .error { color: #ff4466; }
            
            .result-box {
                background: #141425; border-radius: 12px; padding: 20px;
                border: 1px solid #2a2a4a; margin-top: 20px; display: none;
            }
            .result-box.success { border-color: #00ff88; }
            .result-box .title { font-weight: bold; font-size: 1.2rem; margin-bottom: 10px; }
            .result-box .details { color: #8888aa; font-size: 0.9rem; }
            
            .status { text-align: center; color: #666688; font-size: 0.9rem; margin-top: 20px; }
            
            @media (max-width: 700px) { .grid-3 { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏗️ CAIS</h1>
            <p class="subtitle">Sistema Autopoiético - Auto-creación desde Google Drive</p>
            
            <div class="grid-3" id="stats">
                <div class="card"><div class="value" id="fileCount">0</div><div class="label">📄 Archivos en Drive</div></div>
                <div class="card"><div class="value" id="knowledgeCount">0</div><div class="label">📚 Entradas de Conocimiento</div></div>
                <div class="card"><div class="value" id="cycleCount">0</div><div class="label">🔄 Ciclos de Auto-creación</div></div>
            </div>
            
            <div class="actions">
                <button class="btn btn-success" onclick="runFullCycle()">🚀 PROCESAR TODOS LOS ARCHIVOS</button>
                <button class="btn btn-primary" onclick="selfCreateOnly()">🧠 Auto-Crear</button>
                <button class="btn btn-danger" onclick="resetSystem()">🔄 Reiniciar</button>
            </div>
            
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
                <div class="progress-text" id="progressText">Iniciando...</div>
            </div>
            
            <div class="log-container" id="logContainer"></div>
            
            <div class="result-box" id="resultBox">
                <div class="title" id="resultTitle">✅ Completado</div>
                <div class="details" id="resultDetails"></div>
            </div>
            
            <div class="status" id="status">Listo para procesar</div>
        </div>

        <script>
            let isRunning = false;
            
            async function updateStats() {
                try {
                    const r = await fetch('/api/status');
                    const data = await r.json();
                    document.getElementById('fileCount').textContent = data.total_files || 0;
                    document.getElementById('knowledgeCount').textContent = data.knowledge_entries || 0;
                    document.getElementById('cycleCount').textContent = data.self_creation_cycles || 0;
                } catch(e) {}
            }
            
            function addLog(message, type = 'info') {
                const container = document.getElementById('logContainer');
                container.style.display = 'block';
                const time = new Date().toLocaleTimeString();
                const div = document.createElement('div');
                div.className = 'log-line';
                div.innerHTML = `<span class="time">${time}</span><span class="${type}">${message}</span>`;
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            }
            
            function setProgress(percent, text) {
                document.getElementById('progressContainer').style.display = 'block';
                document.getElementById('progressFill').style.width = percent + '%';
                document.getElementById('progressText').textContent = text;
            }
            
            function showResult(title, details, type = 'success') {
                const box = document.getElementById('resultBox');
                box.style.display = 'block';
                box.className = 'result-box ' + type;
                document.getElementById('resultTitle').textContent = title;
                document.getElementById('resultDetails').textContent = details;
            }
            
            async function runFullCycle() {
                if (isRunning) return;
                isRunning = true;
                document.getElementById('status').textContent = '⏳ Procesando...';
                document.getElementById('logContainer').innerHTML = '';
                document.getElementById('resultBox').style.display = 'none';
                
                try {
                    addLog('🚀 Iniciando ciclo autopoiético completo...', 'info');
                    addLog('📂 Obteniendo archivos de Google Drive...', 'info');
                    setProgress(10, 'Obteniendo archivos...');
                    
                    const r1 = await fetch('/api/get_files');
                    const files = await r1.json();
                    addLog(`✅ ${files.total} archivos encontrados en Google Drive`, 'success');
                    setProgress(30, `Descargando ${files.total} archivos...`);
                    
                    const r2 = await fetch('/api/download_all', { method: 'POST' });
                    const download = await r2.json();
                    addLog(`✅ ${download.downloaded} archivos descargados`, 'success');
                    setProgress(60, 'Procesando archivos...');
                    
                    const r3 = await fetch('/api/process_all', { method: 'POST' });
                    const process = await r3.json();
                    addLog(`✅ ${process.files_processed} archivos procesados`, 'success');
                    addLog(`🔑 ${process.keywords_found} palabras clave encontradas`, 'info');
                    addLog(`📋 ${process.patterns_found} patrones encontrados`, 'info');
                    setProgress(85, 'Auto-creando sistema...');
                    
                    const r4 = await fetch('/api/self_create', { method: 'POST' });
                    const create = await r4.json();
                    addLog(`🧠 ${create.modules_generated} módulos generados`, 'success');
                    addLog(`📋 ${create.rules_created} reglas creadas`, 'success');
                    addLog(`🔄 Ciclo de auto-creación #${create.cycles} completado`, 'success');
                    setProgress(100, '✅ ¡Completado!');
                    
                    showResult(
                        '🎉 ¡Ciclo autopoiético completado!',
                        `📄 ${files.total} archivos procesados\n📚 ${process.keywords_found} palabras clave\n🧠 ${create.modules_generated} módulos generados\n🔄 ${create.cycles} ciclos de auto-creación`,
                        'success'
                    );
                    
                    await updateStats();
                    
                } catch(e) {
                    addLog('❌ Error: ' + e.message, 'error');
                    showResult('❌ Error', e.message, 'error');
                }
                
                isRunning = false;
                document.getElementById('status').textContent = '✅ Listo';
            }
            
            async function selfCreateOnly() {
                if (isRunning) return;
                isRunning = true;
                
                try {
                    addLog('🧠 Iniciando auto-creación...', 'info');
                    const r = await fetch('/api/self_create', { method: 'POST' });
                    const data = await r.json();
                    addLog(`✅ ${data.modules_generated} módulos generados`, 'success');
                    addLog(`📋 ${data.rules_created} reglas creadas`, 'success');
                    showResult('🧠 Auto-creación completada', `Módulos: ${data.modules_generated}\nReglas: ${data.rules_created}\nCiclo #${data.cycles}`, 'success');
                    await updateStats();
                } catch(e) {
                    showResult('❌ Error', e.message, 'error');
                }
                
                isRunning = false;
            }
            
            async function resetSystem() {
                if (!confirm('¿Reiniciar el sistema? Se perderán los archivos descargados.')) return;
                try {
                    const r = await fetch('/api/reset', { method: 'POST' });
                    const data = await r.json();
                    showResult('🔄 Sistema reiniciado', data.message, 'warning');
                    document.getElementById('logContainer').innerHTML = '';
                    await updateStats();
                } catch(e) {
                    showResult('❌ Error', e.message, 'error');
                }
            }
            
            // Cargar estadísticas iniciales
            updateStats();
            
            // Actualizar cada 10 segundos
            setInterval(updateStats, 10000);
        </script>
    </body>
    </html>
    """

@app.get("/api/status")
async def get_status():
    config = load_config()
    knowledge = load_knowledge()
    files = get_all_files()
    
    return {
        "total_files": len(files),
        "knowledge_entries": len(knowledge.get("entries", [])),
        "self_creation_cycles": config.get("self_creation_cycles", 0),
        "modules_generated": config.get("modules_generated", 0),
        "rules_count": config.get("rules_count", 0)
    }

@app.get("/api/get_files")
async def api_get_files():
    files = get_all_files()
    return {"total": len(files), "files": [{"name": f.get('name'), "id": f.get('id')} for f in files[:100]]}

@app.post("/api/download_all")
async def api_download_all():
    files = get_all_files()
    downloaded = 0
    failed = 0
    
    # Limpiar directorio de descargas
    for f in DOWNLOAD_DIR.glob("*"):
        if f.is_file():
            f.unlink()
    
    for f in files:
        file_id = f.get('id')
        file_name = f.get('name', 'unknown')
        # Saltar carpetas
        if f.get('mimeType', '').endswith('folder'):
            continue
        result, _ = download_file(file_id, file_name)
        if result:
            downloaded += 1
        else:
            failed += 1
    
    return {"downloaded": downloaded, "failed": failed}

@app.post("/api/process_all")
async def api_process_all():
    result = process_archives()
    return result

@app.post("/api/self_create")
async def api_self_create():
    result = self_create()
    return result

@app.post("/api/reset")
async def api_reset():
    # Limpiar directorios
    for d in [DOWNLOAD_DIR, COMPRESSED_DIR, PROCESSED_DIR]:
        for f in d.glob("*"):
            if f.is_file():
                f.unlink()
    
    # Resetear conocimiento
    save_knowledge({"entries": [], "keywords": [], "patterns": [], "total_files_processed": 0})
    
    config = load_config()
    config["knowledge_entries"] = 0
    save_config(config)
    
    return {"message": "Sistema reiniciado. Archivos limpiados."}

if __name__ == "__main__":
    print("=" * 60)
    print("🏗️ CAIS - SISTEMA AUTOPOIÉTICO COMPLETO")
    print("=" * 60)
    print("🚀 UN SOLO BOTÓN: Procesar TODOS los archivos")
    print("📂 Descarga → Compresión → Extracción → Auto-creación")
    print("🌐 http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
