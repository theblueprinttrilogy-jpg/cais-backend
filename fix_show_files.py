#!/usr/bin/env python3
"""
Script para verificar y forzar la visualización de TODOS los archivos
"""

import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS')

from src.integrations.gdrive_explorer import GDriveExplorer

def get_all_files():
    explorer = GDriveExplorer()
    all_files = []
    page_token = None
    count = 0
    
    print("🔍 Obteniendo TODOS los archivos de Google Drive...")
    
    while True:
        try:
            response = explorer.service.files().list(
                q="trashed=false",
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime)",
                pageToken=page_token
            ).execute()
            
            files = response.get('files', [])
            all_files.extend(files)
            count += len(files)
            print(f"   📄 {count} archivos obtenidos...")
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break
    
    return all_files

if __name__ == "__main__":
    files = get_all_files()
    print(f"\n✅ TOTAL ARCHIVOS ACCESIBLES: {len(files)}")
    
    # Mostrar primeros 10
    print("\n📄 PRIMEROS 10 ARCHIVOS:")
    for i, f in enumerate(files[:10], 1):
        name = f.get('name', 'Unknown')
        mime = f.get('mimeType', '')
        icon = '📁' if 'folder' in mime else '📄'
        print(f"   {i:2}. {icon} {name}")
    
    if len(files) > 10:
        print(f"   ... y {len(files) - 10} archivos más")
