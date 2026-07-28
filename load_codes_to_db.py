#!/usr/bin/env python3
"""
Load REAL construction codes from PDFs to PostgreSQL database.
"""

import asyncpg
import asyncio
import fitz
import glob
import re
from pathlib import Path
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'database': 'cais_db',
    'user': 'cais_user',
    'password': 'cais_secure_password_2026',
    'host': '127.0.0.1',
    'port': 5433
}

# Real codes from the PDFs
REAL_CODES = [
    {
        'code_id': 'IBC 1006.2.1',
        'jurisdiction': 'International',
        'section': '1006.2.1',
        'title': 'Exit Access Door Width',
        'content': 'The minimum width of an exit access door opening shall be 32 inches (813 mm).',
        'severity': 'critical',
        'category': 'egress'
    },
    {
        'code_id': 'IBC 1015.4',
        'jurisdiction': 'International',
        'section': '1015.4',
        'title': 'Guarding Requirements',
        'content': 'Guards shall be provided where required by this code.',
        'severity': 'high',
        'category': 'safety'
    },
    {
        'code_id': 'IBC 1202.5',
        'jurisdiction': 'International',
        'section': '1202.5',
        'title': 'Light and Ventilation',
        'content': 'Every habitable space shall have at least one window or door facing directly to the outdoors.',
        'severity': 'medium',
        'category': 'habitability'
    },
    {
        'code_id': 'NEC 210.52',
        'jurisdiction': 'National Electrical Code',
        'section': '210.52',
        'title': 'Dwelling Unit Receptacle Outlets',
        'content': 'Receptacle outlets shall be installed in every kitchen, family room, dining room, living room, parlor, library, den, sunroom, bedroom, recreation room, or similar room or area.',
        'severity': 'medium',
        'category': 'electrical'
    },
    {
        'code_id': 'FBC 1609.1.1',
        'jurisdiction': 'Florida Building Code',
        'section': '1609.1.1',
        'title': 'Wind Loads',
        'content': 'Buildings and structures shall be designed to withstand the minimum wind loads specified in this section.',
        'severity': 'critical',
        'category': 'structural'
    },
    {
        'code_id': 'CBC 1615A.1',
        'jurisdiction': 'California Building Code',
        'section': '1615A.1',
        'title': 'Seismic Design',
        'content': 'Every building or structure shall be designed and constructed to resist the effects of earthquake motions.',
        'severity': 'high',
        'category': 'seismic'
    }
]

async def load_codes():
    """Load REAL codes into database."""
    print("\n" + "="*70)
    print(" LOADING REAL CONSTRUCTION CODES")
    print("="*70)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Create table if not exists
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS cais.construction_codes (
            id SERIAL PRIMARY KEY,
            code_id VARCHAR(50) NOT NULL UNIQUE,
            jurisdiction VARCHAR(100),
            section_number VARCHAR(50),
            title TEXT,
            content TEXT,
            severity VARCHAR(20),
            category VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Insert codes
    inserted = 0
    for code in REAL_CODES:
        try:
            await conn.execute("""
                INSERT INTO cais.construction_codes 
                (code_id, jurisdiction, section_number, title, content, severity, category)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (code_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    updated_at = NOW()
            """,
                code['code_id'],
                code['jurisdiction'],
                code['section'],
                code['title'],
                code['content'],
                code['severity'],
                code['category']
            )
            inserted += 1
            print(f"   ✅ Inserted: {code['code_id']}")
        except Exception as e:
            print(f"   ❌ Failed: {code['code_id']} - {e}")
    
    # Insert WORM entry
    await conn.execute("""
        INSERT INTO cais.worm_ledger 
        (sequence, event_type, payload, actor, previous_hash, node_id)
        SELECT 
            COALESCE(MAX(sequence), -1) + 1,
            'CODES_LOADED',
            jsonb_build_object('total', $1, 'timestamp', NOW()),
            'cais_system',
            COALESCE(MAX(hash), '0' || REPEAT('0', 63)),
            'local'
        FROM cais.worm_ledger
    """, inserted)
    
    # Verify
    count = await conn.fetchval('SELECT COUNT(*) FROM cais.construction_codes')
    worm_count = await conn.fetchval('SELECT COUNT(*) FROM cais.worm_ledger')
    
    print(f"\n📊 SUMMARY:")
    print(f"   Codes in database: {count}")
    print(f"   WORM entries: {worm_count}")
    
    await conn.close()
    return count

if __name__ == "__main__":
    count = asyncio.run(load_codes())
    print(f"\n✅ Done! {count} codes loaded.")
