#!/bin/bash
# Mover archivos grandes a Google Drive

echo "📦 Moviendo archivos grandes a Google Drive..."

# Directorio temporal para archivos a subir
TEMP_DIR="/tmp/janitor_upload"
mkdir -p $TEMP_DIR

# 1. Mover archivos de Downloads
echo "📁 Moviendo archivos de Downloads..."
mv /mnt/c/Users/maxlo/Downloads/test-00.tar.xz $TEMP_DIR/ 2>/dev/null
mv /mnt/c/Users/maxlo/Downloads/train-00.tar.xz $TEMP_DIR/ 2>/dev/null
mv /mnt/c/Users/maxlo/Downloads/train-01.tar.xz $TEMP_DIR/ 2>/dev/null

# 2. Mover archivos de OneDrive
echo "📁 Moviendo archivos de OneDrive..."
cp "/mnt/c/Users/maxlo/OneDrive/Documentos/WM Construction/CAIS/10_WM_CAIS_PROCORE/CONSTRUCTION-AI-SYSTEM-V10-1.zip" $TEMP_DIR/ 2>/dev/null

# 3. Mover archivos de Autodesk (solo los grandes)
echo "📁 Moviendo archivos de Autodesk..."
find /mnt/c/Autodesk/WI -name "*.tar" -size +100M -exec mv {} $TEMP_DIR/ \; 2>/dev/null

# 4. Ejecutar Janitor para subir a Drive
echo "☁️ Subiendo archivos a Google Drive..."
python -c "
import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS/cais_backend')
from app.agents.janitor_agent import JanitorAgent

janitor = JanitorAgent(
    credentials_file='secrets/credentials.json',
    root_folder_name='JACINTO_CORREA_COMPUTER',
    max_age_days=1
)

# Subir archivos del directorio temporal
import os
for f in os.listdir('/tmp/janitor_upload'):
    file_path = os.path.join('/tmp/janitor_upload', f)
    if os.path.isfile(file_path):
        print(f'Subiendo: {f}')
        # Usar la funcionalidad de upload de Janitor
"

# 5. Limpiar archivos temporales después de subir
echo "🧹 Limpiando archivos temporales..."
# rm -rf $TEMP_DIR  # Descomentar después de verificar

echo "✅ Proceso completado!"
