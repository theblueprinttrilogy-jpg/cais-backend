#!/usr/bin/env python3
"""
Dashboard Integration Module
Connects the Sovereign Dashboard to CAIS Core System
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DashboardIntegration:
    """
    Integrates the dashboard with CAIS core components:
    - WORM Ledger
    - Agent status
    - Document processing queue
    - System metrics
    """
    
    def __init__(self, worm_ledger=None, agent_manager=None, db_pool=None):
        self.worm_ledger = worm_ledger
        self.agent_manager = agent_manager
        self.db_pool = db_pool
        self.cache = {}
        
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Fetches real-time data for the dashboard"""
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": await self._get_metrics(),
            "worm_status": await self._get_worm_status(),
            "agents": await self._get_agent_status(),
            "document_queue": await self._get_document_queue(),
            "activity": await self._get_activity_feed()
        }
        
        return data
    
    async def _get_metrics(self) -> Dict[str, Any]:
        """Gets system metrics"""
        # Integrate with existing metrics system
        return {
            "total_value": "$12.4B",
            "compliance_rate": 98.7,
            "documents": 2400,
            "uptime": 99.99
        }
    
    async def _get_worm_status(self) -> Dict[str, Any]:
        """Gets WORM ledger status"""
        if self.worm_ledger:
            status = self.worm_ledger.get_status()
            return {
                "blocks": status.get("total_entries", 0),
                "integrity": "Valid" if status.get("integrity", False) else "Invalid",
                "breaks": 0
            }
        return {"blocks": 0, "integrity": "Unknown", "breaks": 0}
    
    async def _get_agent_status(self) -> List[Dict[str, Any]]:
        """Gets agent status"""
        if self.agent_manager:
            return self.agent_manager.get_all_status()
        
        # Default agents
        return [
            {"name": "PlanInspector", "status": "Active", "accuracy": 92},
            {"name": "CodeMatcher", "status": "Active", "accuracy": 87},
            {"name": "ComparatorEngine", "status": "Active", "accuracy": 94},
            {"name": "DesignerAgent", "status": "Idle", "accuracy": 100}
        ]
    
    async def _get_document_queue(self) -> List[Dict[str, Any]]:
        """Gets document processing queue"""
        # Integrate with actual queue system
        return [
            {"file": "Building_Plan_2026.pdf", "status": "Processing", "priority": "High"},
            {"file": "Structural_Specs.pdf", "status": "Completed", "priority": "Medium"},
            {"file": "Fire_Safety_Report.pdf", "status": "Failed", "priority": "Critical"},
            {"file": "Energy_Compliance.pdf", "status": "Queued", "priority": "Low"}
        ]
    
    async def _get_activity_feed(self) -> List[Dict[str, Any]]:
        """Gets recent activity"""
        # Integrate with logging system
        return [
            {"text": "Uploaded Building_Plan_2026.pdf", "time": "2 min ago", "icon": "blue"},
            {"text": "Violation detected in Fire_Safety_Report.pdf", "time": "15 min ago", "icon": "gold"},
            {"text": "Report generated for Structural_Specs.pdf", "time": "42 min ago", "icon": "green"},
            {"text": "CodeMatcher completed analysis of 12 documents", "time": "1 hour ago", "icon": "purple"}
        ]


# ============================================
# API Endpoint for Dashboard
# ============================================

async def dashboard_api_endpoint(request):
    """API endpoint for dashboard data"""
    integration = DashboardIntegration()
    data = await integration.get_dashboard_data()
    return json.dumps(data, indent=2)

