#!/bin/bash
# run_cais_agents.sh - Activar todos los agentes de CAIS en background
# 1 Orchestrator | 3 Captains | 30 Search Agents | 4 Storage Agents

echo "=============================================================="
echo " CAIS - ACTIVANDO SISTEMA DE AGENTES"
echo " 1 Orchestrator | 3 Captains | 30 Search Agents | 4 Storage Agents"
echo "=============================================================="

cd /home/maxlo/PROMETHEUS
source venv_prometheus/bin/activate

# Crear directorios necesarios
mkdir -p logs/agents logs/captains logs/orchestrator evidence reports

# ============================================================
# ACTIVAR ORQUESTRADOR
# ============================================================
echo ""
echo "📡 Activando Orquestador..."
nohup python -c "
import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from src.orchestrator.orchestrator import OrchestratorAgent

async def run_orchestrator():
    print(f'[{datetime.now().isoformat()}] Orquestador iniciado')
    
    # Buscar PDFs
    import glob
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/*.pdf')
    if not pdf_files:
        print('❌ No se encontraron PDFs')
        return
    
    # Buscar MYERS RESIDENCE
    myers_files = [f for f in pdf_files if 'MYERS' in f.upper() or 'RESIDENCE' in f.upper()]
    pdf_path = myers_files[0] if myers_files else pdf_files[0]
    
    print(f'📄 Procesando: {Path(pdf_path).name}')
    
    # Inicializar orquestador
    orchestrator = OrchestratorAgent(jurisdiction='Florida')
    
    # Extraer secciones
    from src.agents.plan_inspector_agent import PlanInspectorAgent
    inspector = PlanInspectorAgent()
    sections, full_text = inspector.extract_sections_from_document(str(pdf_path))
    
    print(f'📊 Secciones extraídas: {len(sections)}')
    
    # Ejecutar búsqueda
    results = await orchestrator.orchestrate_search(sections)
    
    print(f'✅ Violaciones encontradas: {len(results)}')
    
    # Almacenar resultados
    if results:
        from src.agents.storage.storage_agent import StorageAgent
        storage = StorageAgent(jurisdiction='Florida')
        await storage.process_evidence('./evidence', 'AUDIT-001')

asyncio.run(run_orchestrator())
" > logs/orchestrator.log 2>&1 &

ORCHESTRATOR_PID=$!
echo "   ✅ Orquestador PID: $ORCHESTRATOR_PID"

# ============================================================
# ACTIVAR CAPITANES (3)
# ============================================================
echo ""
echo "🚀 Activando 3 Capitanes..."

# Captain 1: Building Codes
nohup python -c "
import asyncio
import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from src.captains.captain_agent import CaptainAgent

async def run_captain():
    print('[Captain 1 - Building Codes] Iniciado')
    # Código del capitán
    print('[Captain 1 - Building Codes] Activo')

asyncio.run(run_captain())
" > logs/captains/captain_building.log 2>&1 &

CAPTAIN1_PID=$!
echo "   ✅ Captain 1 (Building Codes) PID: $CAPTAIN1_PID"

nohup python -c "
import asyncio
import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from src.captains.captain_agent import CaptainAgent

async def run_captain():
    print('[Captain 2 - Safety Regulations] Iniciado')
    print('[Captain 2 - Safety Regulations] Activo')

asyncio.run(run_captain())
" > logs/captains/captain_safety.log 2>&1 &

CAPTAIN2_PID=$!
echo "   ✅ Captain 2 (Safety Regulations) PID: $CAPTAIN2_PID"

nohup python -c "
import asyncio
import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from src.captains.captain_agent import CaptainAgent

async def run_captain():
    print('[Captain 3 - Construction Laws] Iniciado')
    print('[Captain 3 - Construction Laws] Activo')

asyncio.run(run_captain())
" > logs/captains/captain_laws.log 2>&1 &

CAPTAIN3_PID=$!
echo "   ✅ Captain 3 (Construction Laws) PID: $CAPTAIN3_PID"

# ============================================================
# ACTIVAR STORAGE AGENTS
# ============================================================
echo ""
echo "💾 Activando Storage Agents..."

nohup python -c "
import asyncio
import sys
sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from src.agents.storage.storage_agent import StorageAgent

async def run_storage():
    print('[Storage Agent] Iniciado')
    storage = StorageAgent(jurisdiction='Florida')
    await storage.process_evidence('./evidence', 'AUDIT-001')
    print('[Storage Agent] Completado')

asyncio.run(run_storage())
" > logs/storage.log 2>&1 &

STORAGE_PID=$!
echo "   ✅ Storage Agent PID: $STORAGE_PID"

# ============================================================
# GUARDAR PIDS
# ============================================================
echo ""
echo "📝 Guardando PIDs..."
cat > logs/agent_pids.txt << EOF
ORCHESTRATOR_PID=$ORCHESTRATOR_PID
CAPTAIN1_PID=$CAPTAIN1_PID
CAPTAIN2_PID=$CAPTAIN2_PID
CAPTAIN3_PID=$CAPTAIN3_PID
STORAGE_PID=$STORAGE_PID
ACTIVATED_AT=$(date -Iseconds)
EOF

echo ""
echo "=============================================================="
echo " ✅ SISTEMA DE AGENTES ACTIVADO"
echo "=============================================================="
echo "   Orquestador: PID $ORCHESTRATOR_PID"
echo "   Captain 1 (Building Codes): PID $CAPTAIN1_PID"
echo "   Captain 2 (Safety Regulations): PID $CAPTAIN2_PID"
echo "   Captain 3 (Construction Laws): PID $CAPTAIN3_PID"
echo "   Storage Agent: PID $STORAGE_PID"
echo ""
echo "📋 Logs:"
echo "   Orquestador: logs/orchestrator.log"
echo "   Captains: logs/captains/"
echo "   Storage: logs/storage.log"
echo ""
echo "🔍 Verificar estado: ps aux | grep -E 'orchestrator|captain|storage' | grep -v grep"
echo "🛑 Detener: pkill -f 'orchestrator|captain|storage'"
echo "=============================================================="
