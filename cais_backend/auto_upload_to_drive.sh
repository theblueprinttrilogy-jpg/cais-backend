#!/bin/bash
# Script para subir archivos automáticamente a Google Drive en background
# Ejecutar: nohup ./auto_upload_to_drive.sh > logs/auto_upload.log 2>&1 &

echo "🚀 Iniciando subida automática a Google Drive..."
echo "📁 Fecha: $(date)"

# Directorio de archivos a subir
DOWNLOAD_DIR="/mnt/c/Users/maxlo/Downloads"
CAIS_DIR="/mnt/c/Users/maxlo/OneDrive/Documentos/WM Construction/CAIS/10_WM_CAIS_PROCORE"

# 1. Crear estructura de carpetas en Drive
echo "📁 Creando carpetas en Google Drive..."
rclone mkdir gdrive-sa:JACINTO_CORREA_COMPUTER/Downloads
rclone mkdir gdrive-sa:JACINTO_CORREA_COMPUTER/CAIS
rclone mkdir gdrive-sa:JACINTO_CORREA_COMPUTER/Autodesk

# 2. Subir archivos de Downloads
echo "📁 Subiendo archivos de Downloads..."
for file in "$DOWNLOAD_DIR"/*.tar.xz "$DOWNLOAD_DIR"/*.zip; do
    if [ -f "$file" ]; then
        echo "📤 Subiendo: $(basename "$file")"
        rclone copy "$file" gdrive-sa:JACINTO_CORREA_COMPUTER/Downloads/ --progress
        if [ $? -eq 0 ]; then
            echo "✅ Subido correctamente: $(basename "$file")"
        else
            echo "❌ Error al subir: $(basename "$file")"
        fi
    fi
done

# 3. Subir archivos de CAIS
echo "📁 Subiendo archivos de CAIS..."
for file in "$CAIS_DIR"/*.zip; do
    if [ -f "$file" ]; then
        echo "📤 Subiendo: $(basename "$file")"
        rclone copy "$file" gdrive-sa:JACINTO_CORREA_COMPUTER/CAIS/ --progress
        if [ $? -eq 0 ]; then
            echo "✅ Subido correctamente: $(basename "$file")"
        else
            echo "❌ Error al subir: $(basename "$file")"
        fi
    fi
done

# 4. Subir archivos de Autodesk
echo "📁 Subiendo archivos de Autodesk..."
if [ -d "/mnt/c/Autodesk/WI" ]; then
    find /mnt/c/Autodesk/WI -name "*.tar" -size +100M -exec rclone copy {} gdrive-sa:JACINTO_CORREA_COMPUTER/Autodesk/ --progress \;
fi

# 5. Verificar archivos subidos
echo "📋 Verificando archivos subidos..."
rclone ls gdrive-sa:JACINTO_CORREA_COMPUTER/

echo "✅ Subida automática completada a las $(date)"
