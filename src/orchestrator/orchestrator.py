#!/usr/bin/env python3
"""
Orchestrator Agent - CAIS - COMPLETE ARCHITECTURE WITH HUMANIZATION
Coordinates all agents: 3 Captains, 30 Search Agents, 4 Storage Agents.
Multi-jurisdiction support with semantic search and evidence generation.
HUMANIZED: Proxies, Cookies, Real IPs, User-Agent rotation.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import sys
import json
import asyncio
import asyncpg
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re
import numpy as np

# For semantic search
from sentence_transformers import SentenceTransformer

# Import agents
from src.captains.captain_agent import CaptainAgent, SearchResult
from src.captains.captain_config import CAPTAIN_DEFINITIONS, get_captain_config
from src.agents.storage.storage_agent import StorageAgent
from src.agents.plan_inspector_agent import PlanInspectorAgent

# Import humanizer
from src.core.humanizer import humanizer


@dataclass
class ViolationReport:
    """Complete violation report from all agents."""
    report_id: str
    jurisdiction: str
    document_name: str
    total_violations: int
    violations: List[Dict]
    captain_results: Dict[str, List[SearchResult]]
    storage_result: Dict
    worm_entry_id: int
    generated_at: str


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking."""
    orchestrator_id: str
    total_sections: int
    total_codes: int
    searches_completed: int
    violations_found: int
    execution_time: float
    agent_breakdown: Dict[str, int]


class OrchestratorAgent:
    """
    Orchestrator Agent - Master coordinator for all CAIS agents.
    HUMANIZED: Uses real IPs, cookies, user-agent rotation.
    
    Architecture:
    - 1 Orchestrator (this)
    - 3 Captains (Building Codes, Safety Regulations, Construction Laws)
    - 30 Search Agents (10 per Captain)
    - 4 Storage Agents (Compressor, Classifier, Renamer, Uploader)
    """
    
    # Category mappings for 3 Captains - FLORIDA PRIORITY URGENTE
    CODE_CATEGORIES = {
        'BuildingCodes': [
            'egress', 'structural', 'habitability', 'foundation', 
            'framing', 'load', 'bearing', 'wall', 'floor', 'roof',
            'beam', 'column', 'joist', 'truss', 'concrete', 'steel',
            'masonry', 'wood', 'framing', 'shear', 'moment', 'deflection',
            'footing', 'slab', 'girder', 'stud', 'rafter'
        ],
        'SafetyRegulations': [
            'safety', 'fire', 'seismic', 'guard', 'handrail', 
            'stair', 'tread', 'riser', 'landing', 'railing',
            'emergency', 'exit', 'smoke', 'alarm', 'sprinkler',
            'guardrail', 'fall', 'protection', 'hazard', 'risk',
            'wind', 'hurricane', 'storm'
        ],
        'ConstructionLaws': [
            'electrical', 'plumbing', 'mechanical', 'energy', 
            'accessibility', 'receptacle', 'outlet', 'circuit',
            'pipe', 'drain', 'vent', 'hvac', 'duct', 'insulation',
            'wiring', 'conduit', 'fixture', 'appliance', 'meter'
        ]
    }
    
    def __init__(self, jurisdiction: str = 'Florida', db_config: Optional[Dict] = None):
        """
        Initialize the Orchestrator Agent with humanization.
        
        Args:
            jurisdiction: Target jurisdiction (e.g., 'Florida', 'California')
            db_config: Database configuration
        """
        self.jurisdiction = jurisdiction
        self.db_config = db_config or {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        
        # Initialize components
        print("📥 Loading embedding model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"   ✅ Model loaded: {self.model.get_sentence_embedding_dimension()} dimensions")
        
        self.storage = StorageAgent(jurisdiction)
        
        # Humanizer is already initialized globally - show its status
        print("\n🧑 HUMANIZER STATUS:")
        print(f"   🌐 Available IPs: {list(humanizer.USER_IPS.keys())}")
        print(f"   🌐 Current IP: {humanizer.current_ip}")
        print(f"   🖥️  User-Agent: {humanizer.current_user_agent[:50]}...")
        print(f"   🍪 Cookies: {len(humanizer.cookies)} entries")
        print(f"   🔌 Proxies: {'Enabled' if humanizer.use_proxy else 'Disabled'}")
        
        # Metrics
        self.metrics = AgentMetrics(
            orchestrator_id=f"ORCH-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            total_sections=0,
            total_codes=0,
            searches_completed=0,
            violations_found=0,
            execution_time=0.0,
            agent_breakdown={}
        )
        
        # Results storage
        self.violations: List[Dict] = []
        self.captain_results: Dict[str, List[SearchResult]] = {}
        self.section_cache: List[Dict] = []
        self.code_cache: List[Dict] = []
        
        print(f"\n🏛️ ORCHESTRATOR AGENT INITIALIZED")
        print(f"   Jurisdiction: {jurisdiction}")
        print(f"   Model: paraphrase-multilingual-MiniLM-L12-v2")
        print(f"   Captains: {len(CAPTAIN_DEFINITIONS)}")
        print(f"   🌐 Current IP: {humanizer.current_ip}")
        print(f"   🍪 Cookies: {len(humanizer.cookies)} entries")
    
    async def get_codes_by_jurisdiction(self) -> List[Dict]:
        """
        Get all codes for the jurisdiction from database.
        HUMANIZED: Uses real IP, cookies, UA rotation.
        """
        # Rotate IP and UA for humanization
        humanizer.rotate()
        
        conn = await asyncpg.connect(**self.db_config)
        try:
            print(f"   🌐 Accessing database with IP: {humanizer.current_ip}")
            print(f"   🖥️  User-Agent: {humanizer.current_user_agent[:50]}...")
            print(f"   🍪 Cookies: {len(humanizer.cookies)} entries")
            
            rows = await conn.fetch("""
                SELECT 
                    id,
                    code_id,
                    jurisdiction,
                    section_number,
                    title,
                    content,
                    severity,
                    category,
                    embedding
                FROM cais.construction_codes
                WHERE jurisdiction ILIKE $1
                ORDER BY severity DESC, code_id
            """, f"%{self.jurisdiction}%")
            
            codes = [dict(row) for row in rows]
            self.code_cache = codes
            self.metrics.total_codes = len(codes)
            
            print(f"   📋 {len(codes)} codes loaded for {self.jurisdiction}")
            
            return codes
            
        except Exception as e:
            print(f"   ❌ Error loading codes: {e}")
            return []
        finally:
            await conn.close()
    
    async def 
        """
        Extract sections from document using PlanInspector.
        HUMANIZED: Uses real IP, cookies, UA rotation.
        """
        # Rotate IP for OCR process
        humanizer.rotate()
        
        print(f"   🌐 Extracting sections with IP: {humanizer.current_ip}")
        
        inspector = PlanInspectorAgent()
        sections, full_text = inspector.extract_sections_from_document(pdf_path)
        
        self.section_cache = sections
        self.metrics.total_sections = len(sections)
        
        print(f"   📄 {len(sections)} sections extracted")
        print(f"   🌐 IP used: {humanizer.current_ip}")
        
        return sections
    
    def categorize_codes(self, codes: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize codes for the 3 Captains.
        """
        categorized = {
            'BuildingCodes': [],
            'SafetyRegulations': [],
            'ConstructionLaws': []
        }
        
        for code in codes:
            code_content = code.get('content', '').lower()
            code_category = code.get('category', '').lower()
            
            # Check each captain's keywords
            for captain_name, keywords in self.CODE_CATEGORIES.items():
                for keyword in keywords:
                    if keyword in code_category or keyword in code_content:
                        categorized[captain_name].append(code)
                        break
        
        # Ensure each captain has at least some codes
        for captain_name in categorized:
            if len(categorized[captain_name]) < 2:
                # Add unassigned codes
                for code in codes:
                    if code not in categorized['BuildingCodes'] and \
                       code not in categorized['SafetyRegulations'] and \
                       code not in categorized['ConstructionLaws']:
                        categorized[captain_name].append(code)
                        if len(categorized[captain_name]) >= 3:
                            break
        
        return categorized
    
    async def orchestrate_search(self, sections: List[Dict]) -> List[Dict]:
        """
        Main orchestration method - coordinates all agents.
        HUMANIZED: All requests use real IPs, cookies, UA rotation.
        
        Returns:
            List of detected violations
        """
        start_time = datetime.now()
        
        # Rotate IP at start of orchestration
        humanizer.rotate()
        
        print("\n" + "="*70)
        print(" ORCHESTRATOR AGENT - STARTING SEARCH")
        print("="*70)
        print(f"   Jurisdiction: {self.jurisdiction}")
        print(f"   Sections: {len(sections)}")
        print(f"   Captains: {len(CAPTAIN_DEFINITIONS)}")
        print(f"   🌐 IP: {humanizer.current_ip}")
        print(f"   🖥️  UA: {humanizer.current_user_agent[:50]}...")
        print(f"   🍪 Cookies: {len(humanizer.cookies)}")
        print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 1. Get codes with humanization
        codes = await self.get_codes_by_jurisdiction()
        if not codes:
            print("   ❌ No codes found. Please add codes for this jurisdiction.")
            return []
        
        # 2. Categorize codes for Captains
        categorized_codes = self.categorize_codes(codes)
        
        print(f"\n📊 CODE DISTRIBUTION BY CAPTAIN:")
        for captain, code_list in categorized_codes.items():
            config = CAPTAIN_DEFINITIONS.get(captain)
            display_name = config.display_name if config else captain
            print(f"   {display_name}: {len(code_list)} codes")
        
        # 3. Initialize Captains
        captains = []
        for name, code_list in categorized_codes.items():
            if code_list:
                config = get_captain_config(name)
                agent_count = config.agent_count if config else 10
                captain = CaptainAgent(
                    name=name,
                    jurisdiction=self.jurisdiction,
                    codes=code_list,
                    agent_count=agent_count
                )
                captains.append(captain)
                display_name = config.display_name if config else name
                print(f"\n   🚀 Captain {display_name} initialized with {len(code_list)} codes")
        
        if not captains:
            print("   ❌ No captains initialized - no codes available")
            return []
        
        # 4. Execute Captains (parallel) with humanization
        print(f"\n🔄 EXECUTING {len(captains)} CAPTAINS IN PARALLEL...")
        
        # Humanize: rotate IP before each captain
        captain_tasks = []
        for captain in captains:
            humanizer.rotate()
            print(f"   🌐 Captain {captain.name} using IP: {humanizer.current_ip}")
            captain_tasks.append(captain.search(sections))
        
        captain_results = await asyncio.gather(*captain_tasks)
        
        # 5. Collect results
        all_violations = []
        for captain, results in zip(captains, captain_results):
            self.captain_results[captain.name] = results
            all_violations.extend(results)
            
            # Track metrics
            self.metrics.agent_breakdown[captain.name] = len(results)
            self.metrics.searches_completed += 1
        
        # 6. Convert to violation format
        violations = []
        for result in all_violations:
            violation = {
                'code_id': result.code_id,
                'section_text': result.section,
                'similarity': result.similarity,
                'severity': result.severity,
                'captain': getattr(result, 'captain', 'Unknown'),
                'agent_id': result.agent_id,
                'jurisdiction': self.jurisdiction,
                'detected_at': datetime.now().isoformat(),
                'ip_used': humanizer.current_ip,
                'user_agent': humanizer.current_user_agent[:50] + '...'
            }
            violations.append(violation)
        
        self.violations = violations
        self.metrics.violations_found = len(violations)
        
        # 7. Store results
        if violations:
            storage_result = await self.storage.store_violations_batch(violations, 'AUDIT-001')
            self.metrics.agent_breakdown['StorageAgent'] = storage_result.get('stored', 0)
        
        # 8. Record WORM entry with humanization data
        worm_id = await self._record_worm_entry(violations)
        
        # 9. Generate report
        report = self._generate_report(worm_id)
        
        # 10. Metrics
        self.metrics.execution_time = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*70)
        print(" ORCHESTRATION COMPLETE")
        print("="*70)
        print(f"   Captains executed: {len(captains)}")
        print(f"   Total violations: {len(violations)}")
        print(f"   Execution time: {self.metrics.execution_time:.2f}s")
        print(f"   🌐 Final IP: {humanizer.current_ip}")
        print(f"   🍪 Cookies: {len(humanizer.cookies)}")
        print("="*70)
        
        return violations
    
    async def _record_worm_entry(self, violations: List[Dict]) -> int:
        """
        Record orchestration results in WORM ledger.
        HUMANIZED: Includes IP and cookies in the record.
        """
        conn = await asyncpg.connect(**self.db_config)
        try:
            result = await conn.fetchrow("""
                INSERT INTO cais.worm_ledger 
                (sequence, event_type, payload, actor, previous_hash, node_id)
                SELECT 
                    COALESCE(MAX(sequence), -1) + 1,
                    'ORCHESTRATION_COMPLETE',
                    jsonb_build_object(
                        'jurisdiction', $1,
                        'total_violations', $2,
                        'captains', $3,
                        'ip', $4,
                        'user_agent', $5,
                        'cookies', $6,
                        'timestamp', NOW()
                    ),
                    'orchestrator_agent',
                    COALESCE(MAX(hash), '0' || REPEAT('0', 63)),
                    'local'
                FROM cais.worm_ledger
            """, 
                self.jurisdiction,
                len(violations),
                json.dumps(list(self.captain_results.keys())),
                humanizer.current_ip,
                humanizer.current_user_agent[:100],
                json.dumps(humanizer.cookies)
            )
            
            return result[0] if result else 0
            
        except Exception as e:
            print(f"   ⚠️ WORM entry failed: {e}")
            return 0
        finally:
            await conn.close()
    
    def _generate_report(self, worm_id: int) -> ViolationReport:
        """
        Generate comprehensive report with humanization metadata.
        """
        report = ViolationReport(
            report_id=f"RPT-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            jurisdiction=self.jurisdiction,
            document_name=self.section_cache[0].get('document_name', 'Unknown') if self.section_cache else 'Unknown',
            total_violations=len(self.violations),
            violations=self.violations,
            captain_results=self.captain_results,
            storage_result=self.metrics.agent_breakdown,
            worm_entry_id=worm_id,
            generated_at=datetime.now().isoformat()
        )
        
        # Save report to file
        report_dir = Path('./reports')
        report_dir.mkdir(exist_ok=True)
        
        report_path = report_dir / f"orchestrator_report_{report.report_id}.json"
        with open(report_path, 'w') as f:
            json.dump({
                'report_id': report.report_id,
                'jurisdiction': report.jurisdiction,
                'total_violations': report.total_violations,
                'violations': report.violations[:50],
                'captain_results': {
                    name: [{
                        'code_id': r.code_id,
                        'similarity': r.similarity,
                        'severity': r.severity
                    } for r in results[:10]]
                    for name, results in report.captain_results.items()
                },
                'humanization': {
                    'ip': humanizer.current_ip,
                    'user_agent': humanizer.current_user_agent,
                    'cookies_count': len(humanizer.cookies),
                    'available_ips': list(humanizer.USER_IPS.keys()),
                    'timestamp': datetime.now().isoformat()
                },
                'worm_entry_id': report.worm_entry_id,
                'generated_at': report.generated_at
            }, f, indent=2, default=str)
        
        print(f"\n📋 Report saved: {report_path}")
        print(f"   🌐 IP: {humanizer.current_ip}")
        print(f"   🍪 Cookies: {len(humanizer.cookies)}")
        print(f"   📋 Available IPs: {list(humanizer.USER_IPS.keys())}")
        
        return report
    
    def get_summary(self) -> Dict:
        """
        Get summary of orchestration results with humanization data.
        """
        return {
            'orchestrator_id': self.metrics.orchestrator_id,
            'jurisdiction': self.jurisdiction,
            'total_violations': self.metrics.violations_found,
            'captains_used': list(self.captain_results.keys()),
            'captain_results': {
                name: len(results) for name, results in self.captain_results.items()
            },
            'execution_time': self.metrics.execution_time,
            'status': 'completed' if self.metrics.violations_found > 0 else 'no_violations',
            'humanization': {
                'ip': humanizer.current_ip,
                'cookies': len(humanizer.cookies),
                'user_agent': humanizer.current_user_agent[:50] + '...' if humanizer.current_user_agent else None,
                'available_ips': list(humanizer.USER_IPS.keys())
            }
        }


async def main():
    """
    Test the Orchestrator Agent with humanization.
    """
    import glob
    
    print("\n" + "="*70)
    print(" ORCHESTRATOR AGENT - TEST RUN")
    print(" 1 Orchestrator | 3 Captains | 30 Search Agents")
    print(" HUMANIZED: Proxies, Cookies, Real IPs")
    print("="*70)
    
    # Find PDF
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/*.pdf')
    if not pdf_files:
        print("❌ No PDFs found")
        return
    
    pdf_path = pdf_files[0]
    print(f"\n📄 PDF: {Path(pdf_path).name}")
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(jurisdiction='Florida')
    
    # Get sections
    sections = await orchestrator.get_sections_from_document(str(pdf_path))
    
    # Run orchestration
    results = await orchestrator.orchestrate_search(sections)
    
    # Show summary
    summary = orchestrator.get_summary()
    print("\n" + "="*70)
    print(" FINAL SUMMARY")
    print("="*70)
    print(f"   Total violations found: {summary['total_violations']}")
    print(f"   Execution time: {summary['execution_time']:.2f}s")
    print(f"   Status: {summary['status']}")
    print(f"   🌐 IP: {summary['humanization']['ip']}")
    print(f"   🍪 Cookies: {summary['humanization']['cookies']}")
    print(f"   📋 Available IPs: {summary['humanization']['available_ips']}")
    
    if results:
        print("\n📋 VIOLATIONS SUMMARY:")
        for i, v in enumerate(results[:10], 1):
            print(f"   {i}. {v.get('code_id', 'Unknown')} - {v.get('severity', 'unknown')} (sim: {v.get('similarity', 0):.3f})")


if __name__ == "__main__":
    asyncio.run(main())
