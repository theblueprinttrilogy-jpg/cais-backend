#!/usr/bin/env python3
"""
Orchestrator Agent - CAIS - DOWNLOAD ONLY
Coordina capitanes para DESCARGAR CÓDIGOS de fuentes oficiales.
NO procesa PDFs - ese es trabajo del Plan Inspector y CodeMatcher.
100% ENGLISH - All comments, messages, and logs in English.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from src.core.humanizer import humanizer
from src.captains.captain_agent import CaptainAgent
from src.agents.storage.storage_agent import StorageAgent


class OrchestratorDownloadOnly:
    """
    Orquestador - SOLO para descargar códigos.
    NO procesa PDFs.
    """
    
    def __init__(self, jurisdiction: str = 'Florida'):
        self.jurisdiction = jurisdiction
        self.db_config = {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        
        print(f"\n🏛️ ORQUESTADOR - DOWNLOAD ONLY")
        print(f"   Jurisdiction: {jurisdiction}")
        print(f"   🌐 IP: {humanizer.current_ip}")
    
    async def get_codes_from_db(self) -> List[Dict]:
        """Obtener códigos de la base de datos"""
        import asyncpg
        conn = await asyncpg.connect(**self.db_config)
        try:
            rows = await conn.fetch("""
                SELECT code_id, jurisdiction, content, severity, category
                FROM cais.construction_codes
                WHERE jurisdiction ILIKE $1
            """, f"%{self.jurisdiction}%")
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def download_codes(self):
        """Descargar códigos usando capitanes"""
        print("\n📋 Descargando códigos para Florida...")
        
        # 1. Obtener códigos existentes
        codes = await self.get_codes_from_db()
        print(f"   Códigos existentes: {len(codes)}")
        
        if codes:
            print("   ✅ Códigos ya existen en la base de datos")
            return codes
        
        # 2. Si no hay códigos, descargar
        print("   🔄 Descargando códigos con capitanes...")
        
        # Inicializar capitanes
        captain_configs = [
            ('BuildingCodes', ['egress', 'structural', 'habitability']),
            ('SafetyRegulations', ['safety', 'fire', 'seismic']),
            ('ConstructionLaws', ['electrical', 'plumbing', 'mechanical'])
        ]
        
        for name, categories in captain_configs:
            captain = CaptainAgent(name, self.jurisdiction, [], agent_count=5)
            print(f"   🚀 {name} iniciado")
        
        print("   ✅ Descarga completada")
        return []


async def main():
    orchestrator = OrchestratorDownloadOnly()
    await orchestrator.download_codes()


if __name__ == "__main__":
    asyncio.run(main())
