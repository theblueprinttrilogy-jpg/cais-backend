#!/usr/bin/env python3
"""
Drag-and-Drop File Upload Server for CAIS
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json

app = FastAPI(title="CAIS Drag-and-Drop Uploader")

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Serve HTML
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAIS Drag & Drop Uploader</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0a0a1a;
                color: #e0e0e0;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                max-width: 900px;
                width: 100%;
                background: #141425;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.8);
                border: 1px solid #2a2a4a;
            }
            h1 {
                color: #00d4ff;
                font-size: 2.2rem;
                margin-bottom: 10px;
                text-align: center;
            }
            .subtitle {
                text-align: center;
                color: #8888aa;
                margin-bottom: 30px;
                font-size: 1.1rem;
            }
            .drop-zone {
                border: 3px dashed #2a2a5a;
                border-radius: 16px;
                padding: 50px 20px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                background: #0e0e22;
                min-height: 300px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            .drop-zone:hover {
                border-color: #00d4ff;
                background: #12123a;
            }
            .drop-zone.dragover {
                border-color: #00ff88;
                background: #0a2a1a;
                transform: scale(1.02);
            }
            .drop-zone .icon {
                font-size: 4rem;
                margin-bottom: 15px;
            }
            .drop-zone p {
                color: #7777aa;
                font-size: 1.2rem;
            }
            .drop-zone .browse-btn {
                margin-top: 20px;
                background: #00d4ff;
                color: #0a0a1a;
                border: none;
                padding: 12px 30px;
                border-radius: 30px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            .drop-zone .browse-btn:hover {
                background: #00ff88;
                transform: scale(1.05);
            }
            #fileInput { display: none; }
            .files-list {
                margin-top: 25px;
                background: #0a0a1a;
                border-radius: 12px;
                padding: 15px;
                max-height: 300px;
                overflow-y: auto;
            }
            .file-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 15px;
                background: #1a1a3a;
                border-radius: 8px;
                margin-bottom: 8px;
                border-left: 3px solid #00d4ff;
            }
            .file-item .name { color: #e0e0ff; }
            .file-item .size { color: #8888aa; font-size: 0.9rem; }
            .file-item .status { color: #00ff88; }
            .file-item .status.error { color: #ff4466; }
            .upload-progress {
                margin-top: 15px;
                background: #1a1a3a;
                border-radius: 8px;
                padding: 15px;
                display: none;
            }
            .upload-progress .bar {
                height: 6px;
                background: #00d4ff;
                border-radius: 3px;
                width: 0%;
                transition: width 0.3s;
            }
            .stats {
                margin-top: 20px;
                display: flex;
                gap: 30px;
                justify-content: center;
                color: #7777aa;
                font-size: 0.9rem;
            }
            .stats span { color: #00d4ff; font-weight: bold; }
            .success-msg {
                color: #00ff88;
                text-align: center;
                margin-top: 15px;
                font-size: 1.1rem;
                display: none;
            }
            @media (max-width: 600px) {
                .container { padding: 20px; }
                h1 { font-size: 1.6rem; }
                .drop-zone { padding: 30px 15px; min-height: 200px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📤 CAIS Drag & Drop</h1>
            <p class="subtitle">Arrastra tus archivos aquí o haz clic para seleccionarlos</p>
            
            <div class="drop-zone" id="dropZone">
                <div class="icon">📁</div>
                <p>Arrastra archivos aquí</p>
                <p style="font-size:0.9rem; color:#555577; margin-top:5px;">o</p>
                <button class="browse-btn" onclick="document.getElementById('fileInput').click()">
                    Seleccionar archivos
                </button>
                <input type="file" id="fileInput" multiple>
            </div>
            
            <div class="upload-progress" id="progressContainer">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span id="progressText">Subiendo...</span>
                    <span id="progressPercent">0%</span>
                </div>
                <div class="bar" id="progressBar"></div>
            </div>
            
            <div class="success-msg" id="successMsg">✅ ¡Archivos subidos exitosamente!</div>
            
            <div class="files-list" id="filesList">
                <div style="color:#555577; text-align:center; padding:20px;">
                    Archivos subidos aparecerán aquí
                </div>
            </div>
            
            <div class="stats">
                <div>📁 <span id="fileCount">0</span> archivos</div>
                <div>💾 <span id="totalSize">0</span> MB</div>
            </div>
        </div>

        <script>
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');
            const filesList = document.getElementById('filesList');
            const fileCount = document.getElementById('fileCount');
            const totalSize = document.getElementById('totalSize');
            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            const progressPercent = document.getElementById('progressPercent');
            const successMsg = document.getElementById('successMsg');
            
            let uploadedCount = 0;
            let uploadedSize = 0;
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                });
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                });
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    uploadFiles(files);
                }
            });
            
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    uploadFiles(fileInput.files);
                }
            });
            
            async function uploadFiles(files) {
                successMsg.style.display = 'none';
                progressContainer.style.display = 'block';
                
                let total = files.length;
                let completed = 0;
                
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    try {
                        const response = await fetch('/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const result = await response.json();
                        completed++;
                        
                        const percent = Math.round((completed / total) * 100);
                        progressBar.style.width = percent + '%';
                        progressPercent.textContent = percent + '%';
                        progressText.textContent = `Subiendo ${completed}/${total}: ${file.name}`;
                        
                        if (result.success) {
                            uploadedCount++;
                            uploadedSize += file.size / (1024 * 1024);
                            updateStats();
                            addFileToList(file.name, file.size, '✅');
                        } else {
                            addFileToList(file.name, file.size, '❌', 'error');
                        }
                        
                    } catch (err) {
                        completed++;
                        addFileToList(file.name, file.size, '❌', 'error');
                    }
                }
                
                progressContainer.style.display = 'none';
                successMsg.style.display = 'block';
                
                setTimeout(() => {
                    successMsg.style.display = 'none';
                }, 3000);
            }
            
            function addFileToList(name, size, status, cls = '') {
                if (document.querySelector('.files-list div') && 
                    document.querySelector('.files-list div').style.color === '#555577') {
                    filesList.innerHTML = '';
                }
                
                const item = document.createElement('div');
                item.className = 'file-item';
                const sizeMB = (size / (1024 * 1024)).toFixed(2);
                item.innerHTML = `
                    <span class="name">${name}</span>
                    <span class="size">${sizeMB} MB</span>
                    <span class="status ${cls}">${status}</span>
                `;
                filesList.prepend(item);
            }
            
            function updateStats() {
                fileCount.textContent = uploadedCount;
                totalSize.textContent = uploadedSize.toFixed(2);
            }
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Guardar el archivo
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path)
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/files")
async def list_files():
    files = []
    for f in UPLOAD_DIR.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return JSONResponse(files)

if __name__ == "__main__":
    print("🚀 CAIS Drag-and-Drop Server starting...")
    print("📂 Upload directory: ./uploads")
    print("🌐 Open: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
