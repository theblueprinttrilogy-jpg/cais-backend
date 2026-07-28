#!/bin/bash
# Janitor Agent - Background Runner
# Ejecuta el Janitor en segundo plano con nohup

cd /home/maxlo/PROMETHEUS
source venv_prometheus/bin/activate

echo "🚀 Iniciando Janitor Agent en background..."
echo "   Logs: /home/maxlo/PROMETHEUS/logs/janitor_bg.log"

nohup python -c "
import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from cais_backend.app.agents.janitor_oauth import JanitorOAuth
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/maxlo/PROMETHEUS/logs/janitor_bg.log'),
        logging.StreamHandler()
    ]
)

janitor = JanitorOAuth(max_age_days=45)

while True:
    try:
        stats = janitor.scan_and_move()
        logging.info(f'✅ Ciclo completado: {stats[\"successful\"]} archivos subidos')
        time.sleep(3600)  # Esperar 1 hora entre ciclos
    except Exception as e:
        logging.error(f'❌ Error: {e}')
        time.sleep(300)  # Esperar 5 minutos si hay error
" > /home/maxlo/PROMETHEUS/logs/janitor_bg.out 2>&1 &

echo "✅ Janitor Agent corriendo en background (PID: $!)"
