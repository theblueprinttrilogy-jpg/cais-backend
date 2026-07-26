cat > ~/PROMETHEUS/src/agents/learning_agent.py << 'EOF'
#!/usr/bin/env python3
"""
Learning Agent - Ephemeral agent that learns from every interaction
Features: Continuous learning, context awareness, user preference tracking
"""

import sys
import json
import uuid
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use absolute imports
from core.dictionary_engine import get_dictionary_engine
from core.translation_service import get_translation_service
from worm.worm_ledger import WormLedger


@dataclass
class Interaction:
    """Records a single interaction"""
    query: str
    response: str
    language: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: str = ""
    feedback: Optional[str] = None
    learning_triggered: bool = False


@dataclass
class UserPreferences:
    """Tracks user preferences"""
    preferred_language: str
    query_history: List[str] = field(default_factory=list)
    terms_searched: List[str] = field(default_factory=list)
    feedback_count: int = 0
    learning_phase: str = "initial"


class LearningAgent:
    """
    Ephemeral agent with continuous learning capabilities.
    Learns from user interactions, feedback, and external sources.
    """
    
    def __init__(self, user_id: str, language: str = "en"):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.language = language
        self.created_at = datetime.now().isoformat()
        self.destroyed_at = None
        
        # Components
        self.dict_engine = get_dictionary_engine()
        self.translation_service = get_translation_service()
        self.worm = WormLedger()
        
        # State
        self.preferences = UserPreferences(preferred_language=language)
        self.interactions: List[Interaction] = []
        self.learned_terms: Dict[str, str] = {}
        self.learning_history: List[Dict] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Learning configuration
        self.learning_threshold = 5
        self.auto_learn = True
        self.feedback_learning = True
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║   🧠 LEARNING AGENT INITIALIZED                             ║
║   User: {user_id}                                           ║
║   Language: {language}                                      ║
║   Session: {self.session_id[:8]}...                         ║
║   Learning: {'✅ ON' if self.auto_learn else '❌ OFF'}                     ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def process_query(self, query: str, context: str = "") -> Dict:
        """Process user query with learning."""
        with self._lock:
            # Detect context if not provided
            if not context:
                context = self._detect_context(query)
            
            interaction = Interaction(
                query=query,
                response="",
                language=self.language,
                context=context
            )
            
            # Translate query to English for processing
            translated_query = self._translate_to_english(query)
            
            # Build response
            response = self._build_response(translated_query, context)
            
            # Translate response to user language
            translated_response = self._translate_to_language(response, self.language)
            
            # Update interaction
            interaction.response = translated_response
            interaction.timestamp = datetime.now().isoformat()
            self.interactions.append(interaction)
            
            # Update preferences
            self._update_preferences(query, translated_query)
            
            # Learn from interaction
            if self.auto_learn:
                self._learn_from_interaction(interaction)
            
            # Check if deep learning is needed
            if len(self.interactions) >= self.learning_threshold:
                self._perform_deep_learning()
            
            # Register in WORM
            self.worm.append_entry(
                event_type="QUERY_PROCESSED",
                data={
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "query": query,
                    "response": translated_response,
                    "context": context,
                    "language": self.language
                },
                actor="system"
            )
            
            return {
                "query": query,
                "response": translated_response,
                "context": context,
                "language": self.language,
                "interaction_count": len(self.interactions),
                "learning_active": self.auto_learn,
                "timestamp": interaction.timestamp
            }
    
    def _detect_context(self, query: str) -> str:
        """Detect construction context from query"""
        query_lower = query.lower()
        contexts = {
            "structural": ["load", "support", "strength", "structural", "frame", "column", "beam", "foundation"],
            "materials": ["concrete", "steel", "wood", "brick", "glass", "material", "properties"],
            "safety": ["safety", "protection", "hazard", "risk", "emergency", "ppe"],
            "legal": ["permit", "inspection", "code", "zoning", "regulation", "compliance"],
            "construction": ["excavation", "scaffolding", "crane", "formwork", "waterproofing"]
        }
        
        for context, keywords in contexts.items():
            if any(keyword in query_lower for keyword in keywords):
                return context
        
        return "general"
    
    def _translate_to_english(self, text: str) -> str:
        """Translate text from user language to English"""
        if self.language == "en":
            return text
        
        result = self.translation_service.translate(
            text, "en", self.language
        )
        return result.get("translation", text)
    
    def _translate_to_language(self, text: str, target_lang: str) -> str:
        """Translate text from English to target language"""
        if target_lang == "en":
            return text
        
        result = self.translation_service.translate(
            text, target_lang, "en"
        )
        return result.get("translation", text)
    
    def _build_response(self, query: str, context: str) -> str:
        """Build response based on query and context."""
        known_terms = []
        all_terms = self.dict_engine.get_all_terms("en")
        
        for term in all_terms:
            if term in query.lower():
                known_terms.append(term)
        
        if known_terms:
            response_parts = []
            for term in known_terms:
                definition = self.dict_engine.get_term_definition(term, "en")
                response_parts.append(f"- {term}: {definition}")
            
            return f"Based on your query about {', '.join(known_terms)}, here are the construction definitions:\n" + "\n".join(response_parts)
        
        return f"I understand you're asking about {context or 'construction'}. Could you provide more specific terms for a detailed response?"
    
    def _update_preferences(self, original_query: str, translated_query: str) -> None:
        """Update user preferences based on query"""
        self.preferences.query_history.append(original_query)
        
        for term in self.dict_engine.get_all_terms("en"):
            if term in translated_query.lower() and term not in self.preferences.terms_searched:
                self.preferences.terms_searched.append(term)
    
    def _learn_from_interaction(self, interaction: Interaction) -> None:
        """Learn from a single interaction."""
        words = interaction.query.split()
        for word in words:
            clean_word = word.strip(".,!?;:()\"'")
            if len(clean_word) > 3 and clean_word not in self.learned_terms:
                translated_word = self._translate_to_english(clean_word)
                if translated_word != clean_word:
                    self.learned_terms[clean_word] = translated_word
                    self.learning_history.append({
                        "type": "new_term",
                        "original": clean_word,
                        "translated": translated_word,
                        "language": self.language,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.translation_service.learn_translation(
                        clean_word, translated_word, self.language, "en"
                    )
    
    def _perform_deep_learning(self) -> None:
        """Perform deep learning session."""
        if len(self.interactions) < self.learning_threshold:
            return
        
        context_counts = {}
        for interaction in self.interactions:
            context = interaction.context or "general"
            context_counts[context] = context_counts.get(context, 0) + 1
        
        if context_counts:
            primary_context = max(context_counts, key=context_counts.get)
            self.preferences.learning_phase = "active"
            
            self.learning_history.append({
                "type": "deep_learning",
                "primary_context": primary_context,
                "context_counts": context_counts,
                "total_interactions": len(self.interactions),
                "timestamp": datetime.now().isoformat()
            })
            
            self.worm.append_entry(
                event_type="DEEP_LEARNING",
                data={
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "primary_context": primary_context,
                    "total_interactions": len(self.interactions)
                },
                actor="system"
            )
    
    def provide_feedback(self, interaction_index: int, feedback: str) -> None:
        """Allow user to provide feedback on a response."""
        if 0 <= interaction_index < len(self.interactions):
            interaction = self.interactions[interaction_index]
            interaction.feedback = feedback
            self.preferences.feedback_count += 1
            
            if self.feedback_learning:
                self.learning_history.append({
                    "type": "feedback",
                    "interaction_index": interaction_index,
                    "feedback": feedback,
                    "timestamp": datetime.now().isoformat()
                })
                
                self.worm.append_entry(
                    event_type="FEEDBACK_RECEIVED",
                    data={
                        "user_id": self.user_id,
                        "feedback": feedback,
                        "interaction_index": interaction_index
                    },
                    actor="system"
                )
    
    def get_learning_summary(self) -> Dict:
        """Get summary of what the agent has learned"""
        return {
            "total_interactions": len(self.interactions),
            "terms_learned": len(self.learned_terms),
            "learning_phase": self.preferences.learning_phase,
            "primary_terms": self.preferences.terms_searched[:10],
            "contexts": list(set(i.context for i in self.interactions)),
            "feedback_count": self.preferences.feedback_count,
            "history": self.learning_history[-20:]
        }
    
    def destroy(self) -> None:
        """Self-destruct and record final learning summary"""
        self.destroyed_at = datetime.now().isoformat()
        
        self.worm.append_entry(
            event_type="AGENT_DESTROYED",
            data={
                "user_id": self.user_id,
                "session_id": self.session_id,
                "total_interactions": len(self.interactions),
                "terms_learned": len(self.learned_terms),
                "final_learning_summary": self.get_learning_summary()
            },
            actor="system"
        )
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║   💀 LEARNING AGENT DESTROYED                               ║
║   User: {self.user_id}                                      ║
║   Interactions: {len(self.interactions)}                    ║
║   Terms Learned: {len(self.learned_terms)}                 ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "language": self.language,
            "created_at": self.created_at,
            "destroyed_at": self.destroyed_at,
            "interactions": len(self.interactions),
            "terms_learned": len(self.learned_terms),
            "preferences": self.preferences.__dict__,
            "learning_active": self.auto_learn
        }


# ============================================
# DEMONSTRATION
# ============================================

def demo():
    """Demonstrate Learning Agent capabilities"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║   🧠 LEARNING AGENT DEMONSTRATION                           ║
║   Agent learns from every interaction                      ║
║   Supports 20 languages with real dictionaries             ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    agent = LearningAgent("demo_user", "es")
    
    queries = [
        "What is a beam?",
        "How does concrete work?",
        "What is scaffolding?",
        "Explain structural load",
        "What is a foundation?"
    ]
    
    print("📌 Simulating 5 interactions:\n")
    for i, query in enumerate(queries, 1):
        print(f"   [{i}] User: {query}")
        result = agent.process_query(query)
        print(f"       CAIS: {result['response'][:80]}...")
        print()
    
    print("📌 Learning Summary:")
    summary = agent.get_learning_summary()
    print(f"   Total interactions: {summary['total_interactions']}")
    print(f"   Terms learned: {summary['terms_learned']}")
    print(f"   Learning phase: {summary['learning_phase']}")
    print(f"   Primary terms: {summary['primary_terms']}")
    
    print("\n📌 Destroying agent...")
    agent.destroy()

if __name__ == "__main__":
    demo()
EOF
