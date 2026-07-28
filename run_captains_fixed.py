#!/usr/bin/env python3
"""
run_captains_fixed.py - Ejecuta los 3 capitanes con sus 10 agentes cada uno
"""

import asyncio
import sys
import json
import glob
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/maxlo/PROMETHEUS')
from src.captains.captain_agent import CaptainAgent, SearchAgent


async def run_captain_with_agents(captain_name: str, category_filter: list, agent_count: int = 10):
    """Ejecuta un capitán con sus agentes de búsqueda"""
    print(f'[{datetime.now().isoformat()}] Captain {captain_name} iniciando...')
    
    # Cargar secciones
    try:
        with open('logs/sections.json', 'r') as f:
            data = json.load(f)
        sections = data['sections']
        print(f'[{captain_name}] 📊 {len(sections)} secciones cargadas')
    except Exception as e:
        print(f'[{captain_name}] ❌ Error cargando secciones: {e}')
        return
    
    # Obtener códigos de la base de datos
    try:
        import asyncpg
        conn = await asyncpg.connect(
            database='cais_db',
            user='cais_user',
            password='cais_secure_password_2026',
            host='127.0.0.1',
            port=5433
        )
        
        codes = await conn.fetch('SELECT code_id, content, severity, category FROM cais.construction_codes WHERE jurisdiction ILIKE $1', '%Florida%')
        await conn.close()
        codes_list = [dict(c) for c in codes]
        print(f'[{captain_name}] 📋 {len(codes_list)} códigos cargados')
    except Exception as e:
        print(f'[{captain_name}] ❌ Error de base de datos: {e}')
        return
    
    # Filtrar códigos por categoría
    filtered_codes = [c for c in codes_list if c.get('category') in category_filter]
    print(f'[{captain_name}] 🔍 {len(filtered_codes)} códigos filtrados para {captain_name}')
    
    if not filtered_codes:
        print(f'[{captain_name}] ⚠️ No hay códigos para esta categoría')
        return
    
    # Crear capitán (esto creará automáticamente los 10 agentes)
    captain = CaptainAgent(captain_name, 'Florida', filtered_codes, agent_count=agent_count)
    
    print(f'[{captain_name}] 🚀 Lanzando {agent_count} agentes de búsqueda...')
    
    # Ejecutar búsqueda
    results = await captain.search(sections)
    
    print(f'[{captain_name}] ✅ Búsqueda completada')
    print(f'[{captain_name}] 📊 Violaciones encontradas: {len(results)}')
    
    # Mostrar resumen de agentes
    for agent_id, count in captain.metrics.agent_breakdown.items():
        if count > 0:
            print(f'[{captain_name}]   🤖 {agent_id}: {count} violaciones')


async def main():
    print("\n" + "="*70)
    print(" EJECUTANDO CAPITANES CON 30 AGENTES DE BÚSQUEDA")
    print("="*70)
    
    # Definir capitanes
    captains = [
        {
            'name': 'BuildingCodes',
            'categories': ['egress', 'structural', 'habitability', 'foundation', 'framing']
        },
        {
            'name': 'SafetyRegulations', 
            'categories': ['safety', 'fire', 'seismic', 'guard', 'handrail', 'stair']
        },
        {
            'name': 'ConstructionLaws',
            'categories': ['electrical', 'plumbing', 'mechanical', 'energy', 'accessibility']
        }
    ]
    
    # Ejecutar capitanes en paralelo
    tasks = []
    for captain_config in captains:
        task = run_captain_with_agents(
            captain_config['name'],
            captain_config['categories'],
            agent_count=10
        )
        tasks.append(task)
    
    # Esperar a que todos terminen
    await asyncio.gather(*tasks)
    
    print("\n" + "="*70)
    print(" ✅ TODOS LOS CAPITANES COMPLETADOS")
    print(" 3 Capitanes | 30 Agentes de Búsqueda")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
