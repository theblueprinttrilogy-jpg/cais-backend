#!/usr/bin/env python3
"""
CAIS - Servidor completo con TODOS los archivos de Google Drive
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import json
from datetime import datetime
from pathlib import Path

from src.integrations.gdrive_explorer import GDriveExplorer
from src.core.logging_config import ForensicLogger

app = FastAPI(title="CAIS - Full Server")
logger = ForensicLogger()

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
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAIS - Google Drive Files</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #0a0a1a;
                color: #e0e0e0;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: #00d4ff; font-size: 2.2rem; margin-bottom: 5px; }
            .subtitle { color: #666688; margin-bottom: 20px; }
            
            .stats {
                display: flex; gap: 30px; flex-wrap: wrap;
                padding: 15px 20px; background: #141425;
                border-radius: 12px; border: 1px solid #2a2a4a;
                margin-bottom: 20px;
            }
            .stats .item { display: flex; align-items: center; gap: 8px; }
            .stats .count { font-weight: bold; font-size: 1.4rem; color: #00d4ff; }
            
            .toolbar {
                display: flex; gap: 12px; flex-wrap: wrap;
                margin-bottom: 20px; align-items: center;
            }
            .toolbar input {
                flex: 1; min-width: 200px; padding: 10px 16px;
                border-radius: 30px; border: 1px solid #2a2a5a;
                background: #0e0e22; color: #e0e0e0; font-size: 1rem;
            }
            .toolbar input:focus { outline: none; border-color: #00d4ff; }
            
            .btn {
                padding: 10px 24px; border: none; border-radius: 30px;
                font-weight: 600; cursor: pointer; transition: all 0.3s;
            }
            .btn:hover { transform: scale(1.05); }
            .btn-primary { background: #00d4ff; color: #0a0a1a; }
            .btn-success { background: #00ff88; color: #0a0a1a; }
            .btn-danger { background: #ff4466; color: white; }
            
            .file-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 8px;
                max-height: 60vh;
                overflow-y: auto;
                padding: 5px;
            }
            .file-grid::-webkit-scrollbar { width: 6px; }
            .file-grid::-webkit-scrollbar-track { background: #0a0a1a; }
            .file-grid::-webkit-scrollbar-thumb { background: #2a2a5a; border-radius: 4px; }
            
            .file-card {
                background: #141425; border-radius: 8px; padding: 10px 14px;
                border: 1px solid #1a1a3a;
                display: flex; align-items: center; gap: 10px;
                transition: all 0.2s;
            }
            .file-card:hover { background: #1a1a35; border-color: #2a2a5a; }
            .file-card .icon { font-size: 1.4rem; flex-shrink: 0; width: 32px; text-align: center; }
            .file-card .info { flex: 1; min-width: 0; }
            .file-card .info .name { 
                font-size: 0.85rem; 
                white-space: nowrap; 
                overflow: hidden; 
                text-overflow: ellipsis; 
            }
            .file-card .info .meta { font-size: 0.65rem; color: #555577; }
            .file-card .size { font-size: 0.7rem; color: #444466; flex-shrink: 0; }
            
            .pagination {
                display: flex; gap: 10px; justify-content: center;
                margin-top: 20px; padding: 10px;
            }
            .pagination button {
                padding: 8px 16px; border: 1px solid #2a2a5a;
                border-radius: 8px; background: transparent;
                color: #e0e0e0; cursor: pointer;
            }
            .pagination button:hover { background: #2a2a5a; }
            .pagination .active { background: #00d4ff; color: #0a0a1a; }
            
            .loading { text-align: center; padding: 40px; color: #666688; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📂 CAIS - Google Drive Files</h1>
            <p class="subtitle">TODOS los archivos accesibles en Google Drive</p>
            
            <div class="stats" id="stats">
                <div class="item">📄 Total: <span class="count" id="totalCount">0</span></div>
                <div class="item">📁 Carpetas: <span class="count" id="folderCount">0</span></div>
                <div class="item">📄 Archivos: <span class="count" id="fileCount">0</span></div>
            </div>
            
            <div class="toolbar">
                <input type="text" id="searchInput" placeholder="🔍 Buscar archivos..." oninput="filterFiles()">
                <button class="btn btn-primary" onclick="loadFiles()">🔄 Recargar</button>
                <button class="btn btn-success" onclick="exportList()">📤 Exportar lista</button>
            </div>
            
            <div id="loading" class="loading">⏳ Cargando archivos...</div>
            <div class="file-grid" id="fileGrid"></div>
            <div class="pagination" id="pagination"></div>
        </div>

        <script>
            let allFiles = [];
            let currentPage = 1;
            const pageSize = 100;
            
            async function loadFiles() {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('fileGrid').innerHTML = '';
                
                try {
                    const response = await fetch('/api/files');
                    allFiles = await response.json();
                    
                    // Actualizar stats
                    const folders = allFiles.filter(f => f.mimeType.includes('folder'));
                    const files = allFiles.filter(f => !f.mimeType.includes('folder'));
                    document.getElementById('totalCount').textContent = allFiles.length;
                    document.getElementById('folderCount').textContent = folders.length;
                    document.getElementById('fileCount').textContent = files.length;
                    
                    renderPage(1);
                } catch (e) {
                    console.error(e);
                }
                document.getElementById('loading').style.display = 'none';
            }
            
            function renderPage(page) {
                currentPage = page;
                const start = (page - 1) * pageSize;
                const end = start + pageSize;
                const pageFiles = allFiles.slice(start, end);
                
                const grid = document.getElementById('fileGrid');
                grid.innerHTML = '';
                
                pageFiles.forEach(f => {
                    const card = document.createElement('div');
                    card.className = 'file-card';
                    
                    const isFolder = f.mimeType.includes('folder');
                    const icon = isFolder ? '📁' : 
                                f.mimeType.includes('pdf') ? '📄' :
                                f.mimeType.includes('image') ? '🖼️' :
                                f.mimeType.includes('document') ? '📝' :
                                f.mimeType.includes('spreadsheet') ? '📊' : '📎';
                    
                    const sizeMB = f.size ? (f.size / (1024 * 1024)).toFixed(2) : '0';
                    const modified = f.modifiedTime ? f.modifiedTime.slice(0, 10) : '';
                    
                    card.innerHTML = `
                        <div class="icon">${icon}</div>
                        <div class="info">
                            <div class="name">${f.name}</div>
                            <div class="meta">${modified} • ${isFolder ? 'Carpeta' : sizeMB + ' MB'}</div>
                        </div>
                        <div class="size">${isFolder ? '📁' : sizeMB + 'MB'}</div>
                    `;
                    grid.appendChild(card);
                });
                
                renderPagination();
            }
            
            function renderPagination() {
                const totalPages = Math.ceil(allFiles.length / pageSize);
                const container = document.getElementById('pagination');
                container.innerHTML = '';
                
                if (totalPages <= 1) return;
                
                for (let i = 1; i <= Math.min(totalPages, 20); i++) {
                    const btn = document.createElement('button');
                    btn.textContent = i;
                    if (i === currentPage) btn.className = 'active';
                    btn.onclick = () => renderPage(i);
                    container.appendChild(btn);
                }
            }
            
            function filterFiles() {
                const query = document.getElementById('searchInput').value.toLowerCase();
                if (!query) {
                    renderPage(1);
                    return;
                }
                
                const filtered = allFiles.filter(f => f.name.toLowerCase().includes(query));
                const grid = document.getElementById('fileGrid');
                grid.innerHTML = '';
                
                filtered.slice(0, 200).forEach(f => {
                    const card = document.createElement('div');
                    card.className = 'file-card';
                    const isFolder = f.mimeType.includes('folder');
                    const icon = isFolder ? '📁' : '📄';
                    card.innerHTML = `
                        <div class="icon">${icon}</div>
                        <div class="info"><div class="name">${f.name}</div></div>
                    `;
                    grid.appendChild(card);
                });
            }
            
            function exportList() {
                let text = '📂 LISTA DE ARCHIVOS EN GOOGLE DRIVE\n';
                text += '=' . repeat(60) + '\n';
                text += `Total: ${allFiles.length} archivos\n\n`;
                
                allFiles.forEach((f, i) => {
                    text += `${i+1}. ${f.name}\n`;
                });
                
                const blob = new Blob([text], { type: 'text/plain' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `google_drive_files_${new Date().toISOString().slice(0,10)}.txt`;
                a.click();
            }
            
            loadFiles();
        </script>
    </body>
    </html>
    """

@app.get("/api/files")
async def api_files():
    files = get_all_files()
    return JSONResponse([{
        "id": f.get('id'),
        "name": f.get('name', 'Unknown'),
        "mimeType": f.get('mimeType', ''),
        "size": f.get('size', 0),
        "modifiedTime": f.get('modifiedTime', ''),
        "parents": f.get('parents', [])
    } for f in files])

if __name__ == "__main__":
    print("🏗️ CAIS - Full Server")
    print("=" * 50)
    print("📂 Mostrando TODOS los archivos de Google Drive")
    print("🌐 Open: http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
