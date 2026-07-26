#!/usr/bin/env python3
"""
CAIS - Servidor simple que muestra TODOS los archivos
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import json
from src.integrations.gdrive_explorer import GDriveExplorer

app = FastAPI()

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

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAIS - Google Drive Files</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0a0a1a; color: #e0e0e0; padding: 20px; }
            h1 { color: #00d4ff; }
            .stats { background: #141425; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
            .stats span { color: #00d4ff; font-weight: bold; }
            input { padding: 10px; width: 300px; border-radius: 20px; border: 1px solid #2a2a5a; background: #0e0e22; color: #e0e0e0; margin-bottom: 20px; }
            .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 8px; max-height: 70vh; overflow-y: auto; }
            .file-card { background: #141425; padding: 10px 14px; border-radius: 8px; border: 1px solid #1a1a3a; display: flex; align-items: center; gap: 10px; }
            .file-card .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .file-card .icon { font-size: 1.2rem; }
            .file-card .size { font-size: 0.7rem; color: #555577; }
            .pagination { margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
            .pagination button { padding: 5px 12px; border: 1px solid #2a2a5a; border-radius: 6px; background: transparent; color: #e0e0e0; cursor: pointer; }
            .pagination button.active { background: #00d4ff; color: #0a0a1a; }
            .loading { text-align: center; padding: 40px; color: #666688; }
        </style>
    </head>
    <body>
        <h1>📂 CAIS - Google Drive Files</h1>
        <div class="stats" id="stats">📄 Cargando...</div>
        <input type="text" id="search" placeholder="🔍 Buscar archivos..." oninput="filterFiles()">
        <div id="loading" class="loading">⏳ Cargando archivos...</div>
        <div class="file-grid" id="fileGrid"></div>
        <div class="pagination" id="pagination"></div>

        <script>
            let allFiles = [];
            let currentPage = 1;
            const pageSize = 100;
            
            async function loadFiles() {
                document.getElementById('loading').style.display = 'block';
                try {
                    const response = await fetch('/api/files');
                    allFiles = await response.json();
                    document.getElementById('stats').innerHTML = 
                        `📄 Total: <span>${allFiles.length}</span> archivos`;
                    renderPage(1);
                } catch(e) { console.error(e); }
                document.getElementById('loading').style.display = 'none';
            }
            
            function renderPage(page) {
                currentPage = page;
                const start = (page - 1) * pageSize;
                const pageFiles = allFiles.slice(start, start + pageSize);
                const grid = document.getElementById('fileGrid');
                grid.innerHTML = '';
                pageFiles.forEach(f => {
                    const isFolder = f.mimeType && f.mimeType.includes('folder');
                    const icon = isFolder ? '📁' : '📄';
                    const size = f.size ? (f.size / (1024*1024)).toFixed(2) : '0';
                    const div = document.createElement('div');
                    div.className = 'file-card';
                    div.innerHTML = `
                        <span class="icon">${icon}</span>
                        <span class="name">${f.name}</span>
                        <span class="size">${isFolder ? 'Carpeta' : size + ' MB'}</span>
                    `;
                    grid.appendChild(div);
                });
                renderPagination();
            }
            
            function renderPagination() {
                const total = Math.ceil(allFiles.length / pageSize);
                const container = document.getElementById('pagination');
                container.innerHTML = '';
                for (let i = 1; i <= Math.min(total, 15); i++) {
                    const btn = document.createElement('button');
                    btn.textContent = i;
                    if (i === currentPage) btn.className = 'active';
                    btn.onclick = () => renderPage(i);
                    container.appendChild(btn);
                }
            }
            
            function filterFiles() {
                const q = document.getElementById('search').value.toLowerCase();
                if (!q) { renderPage(1); return; }
                const filtered = allFiles.filter(f => f.name.toLowerCase().includes(q));
                const grid = document.getElementById('fileGrid');
                grid.innerHTML = '';
                filtered.slice(0, 200).forEach(f => {
                    const div = document.createElement('div');
                    div.className = 'file-card';
                    div.innerHTML = `<span class="icon">📄</span><span class="name">${f.name}</span>`;
                    grid.appendChild(div);
                });
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
        "modifiedTime": f.get('modifiedTime', '')
    } for f in files])

if __name__ == "__main__":
    print("🚀 CAIS Simple Server")
    print("📂 Mostrando TODOS los archivos")
    print("🌐 http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)
