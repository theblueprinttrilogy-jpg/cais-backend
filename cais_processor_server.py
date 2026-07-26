#!/usr/bin/env python3
"""
CAIS - Construction AI System
COMPLETE AUTOPOIETIC SYSTEM
1. Upload → 2. Compress → 3. Read → 4. Feedback → 5. Self-Create
"""

import os
import json
import zipfile
import shutil
import hashlib
import re
import io
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from src.integrations.gdrive_explorer import GDriveExplorer
from src.core.logging_config import ForensicLogger
from src.worm.worm_ledger import WormLedger

app = FastAPI(title="CAIS - Construction AI System")

# Directorios
BASE_DIR = Path(".")
DOWNLOAD_DIR = Path("./downloads")
COMPRESSED_DIR = Path("./compressed")
PROCESSED_DIR = Path("./processed")
METADATA_DIR = Path("./metadata")
CONFIG_DIR = Path("./config")
CODE_DIR = Path("./generated_code")
KNOWLEDGE_DIR = Path("./knowledge")

for d in [DOWNLOAD_DIR, COMPRESSED_DIR, PROCESSED_DIR, METADATA_DIR, 
          CONFIG_DIR, CODE_DIR, KNOWLEDGE_DIR]:
    d.mkdir(exist_ok=True)

logger = ForensicLogger()
worm = WormLedger()

# Archivos de estado
MANIFEST_FILE = METADATA_DIR / "download_manifest.json"
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "knowledge_base.json"
CONFIG_FILE = CONFIG_DIR / "cais_config.json"
RULES_FILE = CONFIG_DIR / "cais_rules.json"

# Configuración inicial
DEFAULT_CONFIG = {
    "system_name": "CAIS - Construction AI System",
    "version": "1.0.0",
    "created_at": datetime.now().isoformat(),
    "knowledge_entries": 0,
    "rules_count": 0,
    "modules_generated": 0,
    "self_creation_cycles": 0,
    "last_update": None
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_knowledge():
    if KNOWLEDGE_FILE.exists():
        with open(KNOWLEDGE_FILE, 'r') as f:
            return json.load(f)
    return {"entries": [], "patterns": {}, "keywords": {}, "rules": []}

def save_knowledge(knowledge):
    with open(KNOWLEDGE_FILE, 'w') as f:
        json.dump(knowledge, f, indent=2)

def load_manifest():
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {"files": {}}

def save_manifest(manifest):
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)

def extract_text_from_pdf(pdf_path):
    """Extrae texto de un archivo PDF"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"[Error extracting PDF: {e}]"

def extract_text_from_txt(txt_path):
    """Extrae texto de un archivo de texto"""
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"[Error reading text: {e}]"

def extract_metadata(file_path):
    """Extrae metadatos de un archivo"""
    stat = file_path.stat()
    return {
        "name": file_path.name,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "extension": file_path.suffix.lower()
    }

def analyze_content(text, filename):
    """Analiza el contenido y extrae patrones"""
    patterns = []
    keywords = []
    
    # Buscar patrones de código
    code_patterns = [
        r'def\s+(\w+)\s*\(',  # Definiciones de funciones
        r'class\s+(\w+)',      # Definiciones de clases
        r'import\s+(\w+)',     # Importaciones
        r'from\s+(\w+)\s+import', # Importaciones específicas
        r'async\s+def\s+(\w+)',  # Funciones asíncronas
    ]
    
    for pattern in code_patterns:
        matches = re.findall(pattern, text)
        if matches:
            patterns.append({
                "pattern": pattern,
                "matches": matches[:10]  # Limitar a 10
            })
    
    # Buscar palabras clave de construcción
    construction_keywords = [
        'construction', 'building', 'structural', 'foundation',
        'concrete', 'steel', 'wood', 'framing', 'roofing',
        'plumbing', 'electrical', 'hvac', 'mechanical',
        'architect', 'engineer', 'contractor', 'project',
        'permit', 'inspection', 'code', 'compliance',
        'safety', 'quality', 'schedule', 'budget'
    ]
    
    text_lower = text.lower()
    for keyword in construction_keywords:
        if keyword in text_lower:
            keywords.append(keyword)
    
    return {
        "patterns": patterns,
        "keywords": keywords,
        "word_count": len(text.split()),
        "char_count": len(text)
    }

def process_zip_for_learning(zip_path):
    """Procesa un archivo ZIP y extrae conocimiento"""
    knowledge = load_knowledge()
    config = load_config()
    
    extracted_files = []
    total_text = ""
    all_patterns = []
    all_keywords = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for file_info in zipf.infolist():
                if file_info.filename.endswith('/'):
                    continue
                
                # Extraer archivo temporalmente
                temp_path = PROCESSED_DIR / file_info.filename
                zipf.extract(file_info, PROCESSED_DIR)
                
                # Procesar según extensión
                ext = file_info.filename.lower()
                content = ""
                metadata = extract_metadata(temp_path)
                
                if ext.endswith('.pdf'):
                    content = extract_text_from_pdf(temp_path)
                elif ext.endswith('.txt') or ext.endswith('.md') or ext.endswith('.csv'):
                    content = extract_text_from_txt(temp_path)
                elif ext.endswith('.json') or ext.endswith('.xml') or ext.endswith('.yaml'):
                    try:
                        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except:
                        content = ""
                else:
                    content = f"[Binary file: {file_info.filename}]"
                
                # Analizar contenido
                if content and len(content) > 50:
                    analysis = analyze_content(content, file_info.filename)
                    all_patterns.extend(analysis.get('patterns', []))
                    all_keywords.extend(analysis.get('keywords', []))
                    total_text += content[:5000]  # Limitar para no saturar
                
                extracted_files.append({
                    "name": file_info.filename,
                    "metadata": metadata,
                    "content_preview": content[:500] if content else "",
                    "size": file_info.file_size
                })
                
                # Limpiar archivo temporal
                if temp_path.exists():
                    temp_path.unlink()
    
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    # Actualizar conocimiento
    if all_keywords:
        knowledge["keywords"] = list(set(knowledge.get("keywords", []) + all_keywords))
    
    if all_patterns:
        knowledge["patterns"] = knowledge.get("patterns", []) + all_patterns
    
    # Crear entrada de conocimiento
    entry = {
        "id": hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
        "source": str(zip_path),
        "processed_at": datetime.now().isoformat(),
        "files_count": len(extracted_files),
        "keywords": list(set(all_keywords)),
        "patterns": all_patterns,
        "text_preview": total_text[:1000]
    }
    
    knowledge["entries"].append(entry)
    knowledge["total_files_processed"] = knowledge.get("total_files_processed", 0) + len(extracted_files)
    
    save_knowledge(knowledge)
    
    # Actualizar configuración
    config["knowledge_entries"] = len(knowledge["entries"])
    config["last_update"] = datetime.now().isoformat()
    config["self_creation_cycles"] = config.get("self_creation_cycles", 0) + 1
    
    save_config(config)
    
    # Registrar en WORM
    worm.append_entry(
        event_type="KNOWLEDGE_EXTRACTED",
        payload={
            "source": str(zip_path),
            "files": len(extracted_files),
            "keywords": len(set(all_keywords)),
            "patterns": len(all_patterns)
        },
        actor="system"
    )
    
    return {
        "success": True,
        "files_processed": len(extracted_files),
        "keywords_found": len(set(all_keywords)),
        "patterns_found": len(all_patterns),
        "knowledge_entries": len(knowledge["entries"])
    }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAIS - Construction AI System</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #0a0a1a;
                color: #e0e0e0;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #00d4ff; font-size: 2.2rem; margin-bottom: 5px; }
            .subtitle { color: #666688; margin-bottom: 20px; }
            .badge { 
                display: inline-block; padding: 4px 12px; border-radius: 20px;
                font-size: 0.7rem; font-weight: bold; margin-left: 10px;
            }
            .badge-cais { background: #00d4ff; color: #0a0a1a; }
            
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
            .card {
                background: #141425; border-radius: 12px; padding: 20px;
                border: 1px solid #2a2a4a;
            }
            .card h3 { color: #00d4ff; margin-bottom: 10px; }
            .card .value { font-size: 2rem; font-weight: bold; color: #00ff88; }
            .card .label { color: #666688; font-size: 0.8rem; }
            
            .toolbar {
                display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px;
                align-items: center; background: #141425; padding: 15px 20px;
                border-radius: 12px; border: 1px solid #2a2a4a;
            }
            .btn {
                padding: 10px 20px; border: none; border-radius: 30px;
                font-weight: 600; cursor: pointer; transition: all 0.3s;
                font-size: 0.9rem;
            }
            .btn:hover { transform: scale(1.05); }
            .btn-primary { background: #00d4ff; color: #0a0a1a; }
            .btn-primary:hover { background: #00ff88; }
            .btn-success { background: #00ff88; color: #0a0a1a; }
            .btn-success:hover { background: #00dd77; }
            .btn-warning { background: #ff8844; color: #0a0a1a; }
            .btn-warning:hover { background: #ffaa44; }
            
            .file-grid {
                display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 10px; max-height: 50vh; overflow-y: auto; padding: 5px;
            }
            .file-card {
                background: #141425; border-radius: 10px; padding: 12px 14px;
                border: 2px solid transparent; cursor: pointer; transition: all 0.2s;
                display: flex; align-items: center; gap: 10px;
            }
            .file-card:hover { border-color: #2a2a5a; background: #1a1a35; }
            .file-card.selected { border-color: #00d4ff; background: #0a1a3a; }
            .file-card .icon { font-size: 1.6rem; flex-shrink: 0; width: 36px; text-align: center; }
            .file-card .info { flex: 1; min-width: 0; }
            .file-card .info .name { font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .file-card .info .meta { font-size: 0.7rem; color: #555577; }
            .file-card .checkbox {
                width: 18px; height: 18px;
                border: 2px solid #2a2a5a;
                border-radius: 4px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
            }
            .file-card.selected .checkbox { background: #00d4ff; border-color: #00d4ff; }
            .file-card.selected .checkbox::after { content: '✓'; color: #0a0a1a; font-weight: bold; font-size: 0.8rem; }
            
            .status-bar {
                margin-top: 15px; background: #141425; border-radius: 12px;
                padding: 15px 20px; border: 1px solid #2a2a4a; display: none;
            }
            .status-bar .bar { height: 6px; background: #00d4ff; border-radius: 3px; width: 0%; transition: width 0.3s; }
            .status-bar .info { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem; color: #8888aa; }
            
            .result-box {
                margin-top: 15px; background: #141425; border-radius: 12px;
                padding: 15px 20px; border: 1px solid #2a2a4a; display: none;
            }
            .result-box.success { border-color: #00ff88; }
            .result-box.error { border-color: #ff4466; }
            .result-box.warning { border-color: #ff8844; }
            .result-box .title { font-weight: bold; font-size: 1rem; margin-bottom: 5px; }
            .result-box .details { font-size: 0.85rem; color: #8888aa; }
            
            .drop-zone {
                border: 2px dashed #2a2a5a; border-radius: 12px; padding: 30px;
                text-align: center; cursor: pointer; transition: all 0.3s;
                background: #0a0a1a;
            }
            .drop-zone:hover { border-color: #00d4ff; }
            .drop-zone.dragover { border-color: #00ff88; background: #0a1a0a; }
            
            @media (max-width: 600px) {
                .grid-2 { grid-template-columns: 1fr; }
                .file-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏗️ CAIS <span style="font-size:0.8rem;color:#666688;">Auto-Creación</span></h1>
            <p class="subtitle">Subir → Comprimir → Leer → Retroalimentar → Auto-crear</p>
            
            <div class="grid-2">
                <div class="card">
                    <h3>📚 Conocimiento</h3>
                    <div class="value" id="knowledgeCount">0</div>
                    <div class="label">Entradas de conocimiento</div>
                </div>
                <div class="card">
                    <h3>🔄 Ciclos</h3>
                    <div class="value" id="cycleCount">0</div>
                    <div class="label">Ciclos de auto-creación</div>
                </div>
            </div>
            
            <div class="drop-zone" id="dropZone">
                <p>📤 Arrastra archivos aquí o haz clic para subirlos</p>
                <input type="file" id="fileInput" multiple style="display:none;">
                <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
                    Seleccionar archivos
                </button>
            </div>
            
            <div class="toolbar">
                <button class="btn btn-success" onclick="processAll()">🔄 Procesar Todo</button>
                <button class="btn btn-warning" onclick="selfCreate()">🧠 Auto-Crear</button>
                <button class="btn btn-primary" onclick="showStatus()">📊 Estado del Sistema</button>
            </div>
            
            <div class="status-bar" id="statusBar">
                <div class="info">
                    <span id="statusText">Procesando...</span>
                    <span id="statusPercent">0%</span>
                </div>
                <div class="bar" id="statusBarProgress"></div>
            </div>
            
            <div class="result-box" id="resultBox">
                <div class="title" id="resultTitle">✅ Completado</div>
                <div class="details" id="resultDetails"></div>
            </div>
        </div>

        <script>
            let allFiles = [];
            let selectedFiles = new Set();
            
            async function loadStatus() {
                const response = await fetch('/api/status');
                const data = await response.json();
                document.getElementById('knowledgeCount').textContent = data.knowledge_entries || 0;
                document.getElementById('cycleCount').textContent = data.self_creation_cycles || 0;
            }
            
            function setupDropZone() {
                const dropZone = document.getElementById('dropZone');
                const fileInput = document.getElementById('fileInput');
                
                dropZone.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                });
                
                dropZone.addEventListener('dragleave', () => {
                    dropZone.classList.remove('dragover');
                });
                
                dropZone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                    if (e.dataTransfer.files.length > 0) {
                        uploadFiles(e.dataTransfer.files);
                    }
                });
                
                fileInput.addEventListener('change', () => {
                    if (fileInput.files.length > 0) {
                        uploadFiles(fileInput.files);
                    }
                });
            }
            
            async function uploadFiles(files) {
                const statusBar = document.getElementById('statusBar');
                const bar = document.getElementById('statusBarProgress');
                const text = document.getElementById('statusText');
                const percent = document.getElementById('statusPercent');
                const resultBox = document.getElementById('resultBox');
                
                statusBar.style.display = 'block';
                resultBox.style.display = 'none';
                
                let completed = 0;
                let success = 0;
                let failed = 0;
                
                for (const file of files) {
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    text.textContent = `📤 Subiendo ${completed+1}/${files.length}: ${file.name}`;
                    const pct = Math.round(((completed+1) / files.length) * 100);
                    bar.style.width = pct + '%';
                    percent.textContent = pct + '%';
                    
                    try {
                        const response = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });
                        const result = await response.json();
                        if (result.success) {
                            success++;
                        } else {
                            failed++;
                        }
                    } catch (e) {
                        failed++;
                    }
                    completed++;
                }
                
                // Procesar automáticamente los archivos subidos
                if (success > 0) {
                    text.textContent = '📚 Procesando archivos para aprendizaje...';
                    bar.style.width = '100%';
                    percent.textContent = '100%';
                    
                    try {
                        const processResponse = await fetch('/api/process_uploads', {
                            method: 'POST'
                        });
                        const processResult = await processResponse.json();
                        
                        resultBox.style.display = 'block';
                        if (processResult.success) {
                            resultBox.className = 'result-box success';
                            document.getElementById('resultTitle').textContent = '✅ ¡Archivos procesados!';
                            document.getElementById('resultDetails').innerHTML = `
                                📄 Subidos: ${success}<br>
                                📚 Archivos procesados: ${processResult.files_processed || 0}<br>
                                🔑 Palabras clave encontradas: ${processResult.keywords_found || 0}<br>
                                📋 Patrones encontrados: ${processResult.patterns_found || 0}
                            `;
                            await loadStatus();
                        } else {
                            resultBox.className = 'result-box error';
                            document.getElementById('resultTitle').textContent = '❌ Error en procesamiento';
                            document.getElementById('resultDetails').textContent = processResult.error || 'Error desconocido';
                        }
                    } catch (e) {
                        resultBox.style.display = 'block';
                        resultBox.className = 'result-box error';
                        document.getElementById('resultTitle').textContent = '❌ Error';
                        document.getElementById('resultDetails').textContent = e.message;
                    }
                }
                
                statusBar.style.display = 'none';
            }
            
            async function processAll() {
                const resultBox = document.getElementById('resultBox');
                const statusBar = document.getElementById('statusBar');
                const bar = document.getElementById('statusBarProgress');
                const text = document.getElementById('statusText');
                const percent = document.getElementById('statusPercent');
                
                statusBar.style.display = 'block';
                resultBox.style.display = 'none';
                
                text.textContent = '📚 Procesando todos los archivos...';
                bar.style.width = '50%';
                percent.textContent = '50%';
                
                try {
                    const response = await fetch('/api/process_all', {
                        method: 'POST'
                    });
                    const result = await response.json();
                    
                    resultBox.style.display = 'block';
                    if (result.success) {
                        resultBox.className = 'result-box success';
                        document.getElementById('resultTitle').textContent = '✅ ¡Procesamiento completado!';
                        document.getElementById('resultDetails').innerHTML = `
                            📚 Archivos procesados: ${result.files_processed || 0}<br>
                            🔑 Palabras clave encontradas: ${result.keywords_found || 0}<br>
                            📋 Patrones encontrados: ${result.patterns_found || 0}<br>
                            🧠 Entradas de conocimiento: ${result.knowledge_entries || 0}
                        `;
                        await loadStatus();
                    } else {
                        resultBox.className = 'result-box error';
                        document.getElementById('resultTitle').textContent = '❌ Error en procesamiento';
                        document.getElementById('resultDetails').textContent = result.error || 'Error desconocido';
                    }
                } catch (e) {
                    resultBox.style.display = 'block';
                    resultBox.className = 'result-box error';
                    document.getElementById('resultTitle').textContent = '❌ Error';
                    document.getElementById('resultDetails').textContent = e.message;
                }
                
                statusBar.style.display = 'none';
            }
            
            async function selfCreate() {
                const resultBox = document.getElementById('resultBox');
                
                resultBox.style.display = 'block';
                resultBox.className = 'result-box warning';
                document.getElementById('resultTitle').textContent = '🧠 Auto-Creación iniciada...';
                document.getElementById('resultDetails').textContent = 'El sistema se está auto-creando a partir del conocimiento adquirido...';
                
                try {
                    const response = await fetch('/api/self_create', {
                        method: 'POST'
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        resultBox.className = 'result-box success';
                        document.getElementById('resultTitle').textContent = '🧠 ¡Auto-Creación completada!';
                        document.getElementById('resultDetails').innerHTML = `
                            📦 Módulos generados: ${result.modules_generated || 0}<br>
                            📋 Reglas creadas: ${result.rules_created || 0}<br>
                            🔄 Ciclos de auto-creación: ${result.cycles || 0}<br>
                            📁 Código generado en: ./generated_code/
                        `;
                        await loadStatus();
                    } else {
                        resultBox.className = 'result-box error';
                        document.getElementById('resultTitle').textContent = '❌ Error en auto-creación';
                        document.getElementById('resultDetails').textContent = result.error || 'Error desconocido';
                    }
                } catch (e) {
                    resultBox.className = 'result-box error';
                    document.getElementById('resultTitle').textContent = '❌ Error';
                    document.getElementById('resultDetails').textContent = e.message;
                }
            }
            
            async function showStatus() {
                const response = await fetch('/api/status');
                const data = await response.json();
                const resultBox = document.getElementById('resultBox');
                
                resultBox.style.display = 'block';
                resultBox.className = 'result-box success';
                document.getElementById('resultTitle').textContent = '📊 Estado del Sistema';
                document.getElementById('resultDetails').innerHTML = `
                    🔄 Ciclos de auto-creación: ${data.self_creation_cycles || 0}<br>
                    📚 Entradas de conocimiento: ${data.knowledge_entries || 0}<br>
                    📋 Reglas: ${data.rules_count || 0}<br>
                    📦 Módulos generados: ${data.modules_generated || 0}<br>
                    📁 Archivos procesados: ${data.files_processed || 0}<br>
                    🔑 Palabras clave: ${data.keywords_count || 0}<br>
                    📅 Última actualización: ${data.last_update || 'Nunca'}
                `;
            }
            
            setupDropZone();
            loadStatus();
        </script>
    </body>
    </html>
    """

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = DOWNLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Registrar en manifiesto
        manifest = load_manifest()
        manifest["files"][file.filename] = {
            "uploaded_at": datetime.now().isoformat(),
            "size": len(content),
            "path": str(file_path)
        }
        save_manifest(manifest)
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "size": len(content)
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/api/process_uploads")
async def process_uploads():
    try:
        # Buscar archivos en downloads
        files = list(DOWNLOAD_DIR.glob("*"))
        if not files:
            return JSONResponse({
                "success": False,
                "error": "No hay archivos para procesar"
            })
        
        # Crear ZIP con todos los archivos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"CAIS_Data_{timestamp}.zip"
        zip_path = COMPRESSED_DIR / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                zipf.write(file_path, file_path.name)
        
        # Procesar ZIP para aprendizaje
        result = process_zip_for_learning(zip_path)
        
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/api/process_all")
async def process_all():
    try:
        # Buscar todos los archivos ZIP en compressed
        zip_files = list(COMPRESSED_DIR.glob("*.zip"))
        if not zip_files:
            return JSONResponse({
                "success": False,
                "error": "No hay archivos ZIP para procesar"
            })
        
        total_files = 0
        total_keywords = 0
        total_patterns = 0
        total_entries = 0
        
        for zip_path in zip_files:
            result = process_zip_for_learning(zip_path)
            if result.get("success"):
                total_files += result.get("files_processed", 0)
                total_keywords += result.get("keywords_found", 0)
                total_patterns += result.get("patterns_found", 0)
                total_entries = result.get("knowledge_entries", 0)
        
        return JSONResponse({
            "success": True,
            "files_processed": total_files,
            "keywords_found": total_keywords,
            "patterns_found": total_patterns,
            "knowledge_entries": total_entries
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/api/self_create")
async def self_create():
    try:
        config = load_config()
        knowledge = load_knowledge()
        
        # Generar código a partir del conocimiento
        modules_generated = 0
        rules_created = 0
        
        # Crear módulo a partir de patrones encontrados
        if knowledge.get("patterns"):
            module_code = generate_module_from_patterns(knowledge["patterns"])
            if module_code:
                module_path = CODE_DIR / f"auto_module_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                with open(module_path, 'w') as f:
                    f.write(module_code)
                modules_generated += 1
        
        # Crear reglas a partir de palabras clave
        if knowledge.get("keywords"):
            rules = generate_rules_from_keywords(knowledge["keywords"])
            if rules:
                with open(RULES_FILE, 'w') as f:
                    json.dump(rules, f, indent=2)
                rules_created = len(rules)
        
        # Actualizar configuración
        config["modules_generated"] = config.get("modules_generated", 0) + modules_generated
        config["rules_count"] = config.get("rules_count", 0) + rules_created
        config["self_creation_cycles"] = config.get("self_creation_cycles", 0) + 1
        config["last_update"] = datetime.now().isoformat()
        save_config(config)
        
        # Registrar en WORM
        worm.append_entry(
            event_type="SELF_CREATION",
            payload={
                "modules_generated": modules_generated,
                "rules_created": rules_created,
                "cycle": config["self_creation_cycles"]
            },
            actor="system"
        )
        
        return JSONResponse({
            "success": True,
            "modules_generated": modules_generated,
            "rules_created": rules_created,
            "cycles": config["self_creation_cycles"]
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

def generate_module_from_patterns(patterns):
    """Genera un módulo Python a partir de patrones encontrados"""
    imports = set()
    functions = []
    classes = []
    
    for pattern in patterns:
        for match in pattern.get("matches", []):
            if match:
                functions.append(f"    def {match}(self, *args, **kwargs):\n        pass")
    
    if not functions and not classes:
        return None
    
    code = f'''"""
Módulo auto-generado por CAIS
Fecha: {datetime.now().isoformat()}
Basado en patrones encontrados en documentos
"""

class AutoModule:
    """Módulo generado automáticamente a partir de patrones"""
    
    def __init__(self):
        self.name = "AutoModule"
        self.version = "1.0.0"
        self.generated_at = "{datetime.now().isoformat()}"
    
{chr(10).join(functions)}
'''
    return code

def generate_rules_from_keywords(keywords):
    """Genera reglas a partir de palabras clave"""
    rules = []
    for keyword in keywords:
        rules.append({
            "id": f"RULE_{keyword.upper()}",
            "keyword": keyword,
            "description": f"Regla generada automáticamente para '{keyword}'",
            "priority": "medium",
            "generated_at": datetime.now().isoformat()
        })
    return rules

@app.get("/api/status")
async def get_status():
    config = load_config()
    knowledge = load_knowledge()
    
    return JSONResponse({
        "self_creation_cycles": config.get("self_creation_cycles", 0),
        "knowledge_entries": config.get("knowledge_entries", 0),
        "rules_count": config.get("rules_count", 0),
        "modules_generated": config.get("modules_generated", 0),
        "files_processed": knowledge.get("total_files_processed", 0),
        "keywords_count": len(knowledge.get("keywords", [])),
        "last_update": config.get("last_update")
    })

if __name__ == "__main__":
    print("🏗️ CAIS - Construction AI System")
    print("=" * 60)
    print("📂 Download dir: ./downloads")
    print("📦 Compressed dir: ./compressed")
    print("📚 Knowledge dir: ./knowledge")
    print("🧠 Generated code dir: ./generated_code")
    print("🌐 Open: http://localhost:8000")
    print("=" * 60)
    print("🔄 CICLO AUTOPOIÉTICO:")
    print("   1. 📤 Subir archivos (drag-and-drop)")
    print("   2. 📚 Procesar para aprendizaje")
    print("   3. 🧠 Auto-creación (generar código)")
    print("   4. 📊 Ver estado del sistema")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
