#!/usr/bin/env python3
"""
Download and Categorize - Descarga archivos de Google Drive y los categoriza
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.gdrive_explorer import GDriveExplorer
from src.integrations.category_manager import CategoryManager
from src.integrations.document_processor import DocumentProcessor

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     📥 DOWNLOAD AND CATEGORIZE                           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Inicializar
    explorer = GDriveExplorer()
    category_manager = CategoryManager()
    processor = DocumentProcessor()
    
    # Verificar que el servicio de Drive está inicializado
    if not explorer.service:
        print("❌ Google Drive service not initialized.")
        print("   Please check your credentials in:")
        print("   ~/PROMETHEUS/config/security/gdrive-credentials.json")
        return
    
    # Listar archivos
    print("📁 Exploring Google Drive...")
    files = explorer._list_files()
    print(f"   Found {len(files)} files")
    
    if not files:
        print("   No files found.")
        return
    
    # Mostrar primeros 5 archivos
    print("\n📄 First 5 files:")
    for f in files[:5]:
        print(f"   - {f.name} ({f.mime_type})")
    
    # Categorizar automáticamente
    categories = {
        'constitution': ['plan', 'workplan', 'system', 'architecture', 'wm'],
        'laws': ['ibc', 'building', 'code', 'regulations', 'compliance'],
        'reports': ['report', 'analysis', 'summary'],
        'technical': ['technical', 'specification', 'manual'],
        'design': ['design', 'drawing', 'plan']
    }
    
    print("\n📂 Auto-categorizing files...")
    for category, patterns in categories.items():
        for pattern in patterns:
            matching = [f for f in files if pattern.lower() in f.name.lower()]
            if matching:
                file_ids = [f.id for f in matching]
                category_manager.add_files(category, file_ids)
                print(f"   {category}: {len(matching)} files")
    
    # Mostrar estadísticas
    category_manager.show_statistics()

if __name__ == "__main__":
    main()
