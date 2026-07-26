#!/usr/bin/env python3
"""
CAIS - Unified Construction Code Compliance System
User interacts with CAIS, not with agents.
"""

import sys
import json
import uuid
import gc
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import weakref

# Add root directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.ephemeral_agent import EphemeralAgent
from worm.worm_ledger import WormLedger


class CAISSystem:
    """
    Unified CAIS System - User only sees this.
    Agents are ephemeral and invisible.
    """
    
    def __init__(self):
        self.worm = WormLedger()
        self.active_sessions = {}
        self._lock = threading.Lock()
        self._total_sessions = 0
        
        # Load available languages
        self.languages = self._load_languages()
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║   🏗️  CAIS - Construction Code Compliance System           ║
║   Autonomous Building Code Supervision                     ║
║   Active sessions: 0                                      ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def _load_languages(self) -> Dict:
        """Load available languages"""
        lang_file = Path("~/PROMETHEUS/dictionaries/languages.json").expanduser()
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def start_session(self, user_id: str, language: str = "en") -> Dict:
        """
        Start a new session for a user.
        Creates an invisible ephemeral agent.
        
        Args:
            user_id: User identifier
            language: Native language code
            
        Returns:
            Dict with session information
        """
        with self._lock:
            # Check if user already has an active session
            if user_id in self.active_sessions:
                return self._get_session_info(user_id)
            
            # Create ephemeral agent (invisible to user)
            agent = EphemeralAgent(user_id, language)
            
            # Save session
            session_id = str(uuid.uuid4())
            self.active_sessions[user_id] = {
                "session_id": session_id,
                "agent": agent,
                "language": language,
                "created_at": datetime.now().isoformat(),
                "interactions": 0
            }
            self._total_sessions += 1
            
            # Register in WORM
            self.worm.append_entry(
                event_type="SESSION_STARTED",
                data={
                    "user_id": user_id,
                    "session_id": session_id,
                    "language": language
                },
                actor="system"
            )
            
            return {
                "status": "started",
                "session_id": session_id,
                "user_id": user_id,
                "language": language,
                "available_languages": list(self.languages.keys())
            }
    
    def process_query(self, user_id: str, query: str) -> Dict:
        """
        Process a user query.
        User believes they are talking to CAIS.
        
        Args:
            user_id: User identifier
            query: Query in native language
            
        Returns:
            Dict with response
        """
        with self._lock:
            # Check active session
            if user_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "No active session. Use 'start_session' first."
                }
            
            session = self.active_sessions[user_id]
            agent = session["agent"]
            language = session["language"]
            session["interactions"] += 1
            
            # Agent processes the query
            result = agent.process_query(query)
            
            # Register in WORM
            self.worm.append_entry(
                event_type="QUERY_PROCESSED",
                data={
                    "user_id": user_id,
                    "session_id": session["session_id"],
                    "query": query,
                    "language": language
                },
                actor="system"
            )
            
            # Return response as if CAIS generated it
            return {
                "status": "success",
                "response": result.get("response", "Processing your query..."),
                "language": language
            }
    
    def end_session(self, user_id: str) -> Dict:
        """
        End a user session.
        The agent self-destructs.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with confirmation
        """
        with self._lock:
            if user_id not in self.active_sessions:
                return {"status": "error", "message": "No active session"}
            
            session = self.active_sessions[user_id]
            agent = session["agent"]
            session_id = session["session_id"]
            
            # Register in WORM
            self.worm.append_entry(
                event_type="SESSION_ENDED",
                data={
                    "user_id": user_id,
                    "session_id": session_id,
                    "interactions": session["interactions"]
                },
                actor="system"
            )
            
            # Destroy agent (invisible to user)
            agent.destroy()
            
            # Remove session
            del self.active_sessions[user_id]
            
            # Force garbage collection
            gc.collect()
            
            return {
                "status": "ended",
                "user_id": user_id,
                "session_id": session_id,
                "total_interactions": session["interactions"]
            }
    
    def get_status(self) -> Dict:
        """Get system status (visible to administrators)"""
        return {
            "active_sessions": len(self.active_sessions),
            "total_sessions_created": self._total_sessions,
            "available_languages": list(self.languages.keys()),
            "worm_status": self.worm.get_status(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_session_info(self, user_id: str) -> Dict:
        """Get information about an active session"""
        session = self.active_sessions.get(user_id)
        if not session:
            return {"status": "no_session"}
        
        return {
            "status": "active",
            "session_id": session["session_id"],
            "language": session["language"],
            "created_at": session["created_at"],
            "interactions": session["interactions"]
        }
    
    def get_available_languages(self) -> Dict:
        """Get available languages for the user"""
        return self.languages


# ============================================
# GLOBAL INSTANCE (Singleton)
# ============================================

_cais_instance = None

def get_cais() -> CAISSystem:
    """Get the single CAIS instance (Singleton)"""
    global _cais_instance
    if _cais_instance is None:
        _cais_instance = CAISSystem()
    return _cais_instance


# ============================================
# DEMONSTRATION - USER INTERACTS WITH CAIS
# ============================================

def demo():
    """
    Demonstration: User interacts with CAIS, not with agents.
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║   🏗️  CAIS - UNIFIED SYSTEM                                 ║
║   User only sees CAIS, not the agents                      ║
║   Agents work in the background                            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Get CAIS instance
    cais = get_cais()
    
    print("📌 STEP 1: User starts CAIS session")
    user_id = "architect_001"
    result = cais.start_session(user_id, "es")
    print(f"   ✅ Session started: {result['session_id']}")
    print(f"   🌐 Language: {result['language']}")
    
    print("\n📌 STEP 2: User queries CAIS")
    query = "What is a beam in construction?"
    result = cais.process_query(user_id, query)
    print(f"   ❓ User: {query}")
    print(f"   💬 CAIS: {result['response']}")
    
    print("\n📌 STEP 3: User asks another question")
    query = "How is column load calculated?"
    result = cais.process_query(user_id, query)
    print(f"   ❓ User: {query}")
    print(f"   💬 CAIS: {result['response']}")
    
    print("\n📌 STEP 4: Check system status")
    status = cais.get_status()
    print(f"   📊 Active sessions: {status['active_sessions']}")
    print(f"   📊 Total sessions created: {status['total_sessions_created']}")
    print(f"   🌐 Available languages: {status['available_languages']}")
    
    print("\n📌 STEP 5: User ends session")
    result = cais.end_session(user_id)
    print(f"   ✅ Session closed: {result['status']}")
    print(f"   📊 Total interactions: {result['total_interactions']}")
    
    print("\n📌 STEP 6: Verify agent was destroyed")
    status = cais.get_status()
    print(f"   📊 Active sessions: {status['active_sessions']}")
    print(f"   📊 WORM entries: {status['worm_status']['total_entries']}")
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║   ✅ DEMONSTRATION COMPLETE                                  ║
║   User interacted with CAIS without knowing about agents   ║
║   Agents were created and destroyed automatically         ║
║   Everything was recorded in the WORM Ledger              ║
╚══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    demo()
