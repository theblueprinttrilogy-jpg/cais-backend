#!/usr/bin/env python3
"""
Agente Efímero - Se crea, atiende y se autodestruye.
Cada usuario tiene su propio agente que desaparece cuando termina.
"""

import json
import uuid
import weakref
import gc
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import threading

class EphemeralAgent:
    """
    Agente que vive solo durante la sesión del usuario.
    Al finalizar, se autodestruye y libera todos los recursos.
    """
    
    # Contador global de agentes activos
    _active_agents = 0
    _total_agents_created = 0
    _lock = threading.Lock()
    
    def __init__(self, user_id: str, target_language: str = "es"):
        """
        Crear un agente efímero para un usuario específico
        
        Args:
            user_id: Identificador único del usuario
            target_language: Código del idioma nativo
        """
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.target_language = target_language
        self.created_at = datetime.now().isoformat()
        self.destroyed_at = None
        
        # Cargar datos (compartidos entre agentes para ahorrar memoria)
        self.shared_data = self._load_shared_data()
        
        # Datos específicos del agente
        self.context = {}
        self.history = []
        
        # Registrar creación
        with EphemeralAgent._lock:
            EphemeralAgent._active_agents += 1
            EphemeralAgent._total_agents_created += 1
        
        print(f"🧠 Agente creado: {self.session_id[:8]}...")
        print(f"   👤 Usuario: {user_id}")
        print(f"   🌐 Idioma: {target_language}")
        print(f"   📊 Agentes activos: {EphemeralAgent._active_agents}")
        
        # Auto-registrar para autodestrucción
        self._setup_destructor()
    
    def _load_shared_data(self) -> Dict:
        """Cargar datos compartidos entre agentes (leer una vez)"""
        # Diccionarios semánticos
        semantic_dir = Path("~/PROMETHEUS/dictionaries/semantic").expanduser()
        construction_dir = Path("~/PROMETHEUS/dictionaries/construction").expanduser()
        
        data = {
            "semantic": {},
            "construction": {},
            "languages": {}
        }
        
        # Cargar idiomas
        lang_file = Path("~/PROMETHEUS/dictionaries/languages.json").expanduser()
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                data["languages"] = json.load(f)
        
        # Cargar diccionario semántico
        sem_file = semantic_dir / f"en_to_{self.target_language}.json"
        if sem_file.exists():
            with open(sem_file, 'r', encoding='utf-8') as f:
                data["semantic"] = json.load(f)
        
        # Cargar diccionario de construcción
        const_file = construction_dir / f"construction_{self.target_language}.json"
        if const_file.exists():
            with open(const_file, 'r', encoding='utf-8') as f:
                data["construction"] = json.load(f)
        
        return data
    
    def _setup_destructor(self):
        """Configurar el mecanismo de autodestrucción"""
        # Usar weakref para detectar cuando el agente ya no se usa
        self._finalizer = weakref.finalize(self, self._destroy)
    
    @classmethod
    def _destroy(cls):
        """Método de autodestrucción"""
        with cls._lock:
            cls._active_agents -= 1
        print(f"💀 Agente destruido. Agentes activos: {cls._active_agents}")
        gc.collect()  # Forzar recolección de memoria
    
    def speak(self, text: str) -> str:
        """
        Hablar en el idioma nativo del usuario
        
        Args:
            text: Texto en inglés
            
        Returns:
            Texto traducido al idioma nativo
        """
        # Simular traducción
        # En producción, esto usaría el diccionario real
        return f"[{self.target_language}] {text}"
    
    def process_query(self, query: str) -> Dict:
        """
        Procesar una consulta del usuario
        """
        # Registrar en historial
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query
        })
        
        # Procesar (simulación)
        response = {
            "query": query,
            "response": f"Procesando consulta en {self.target_language}: {query}",
            "agent_id": self.session_id,
            "language": self.target_language
        }
        
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "response": response
        })
        
        return response
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas del agente"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "language": self.target_language,
            "created_at": self.created_at,
            "destroyed_at": self.destroyed_at,
            "history_count": len(self.history),
            "active_agents": EphemeralAgent._active_agents,
            "total_agents_created": EphemeralAgent._total_agents_created
        }
    
    def destroy(self):
        """Destruir el agente manualmente"""
        self.destroyed_at = datetime.now().isoformat()
        print(f"🔄 Destruyendo agente {self.session_id[:8]}...")
        self._finalizer()


class AgentFactory:
    """
    Fábrica de agentes efímeros - Crea agentes bajo demanda
    """
    
    @staticmethod
    def create_agent(user_id: str, language: str = "es") -> EphemeralAgent:
        """
        Crear un nuevo agente efímero para un usuario
        
        Args:
            user_id: Identificador del usuario
            language: Código del idioma nativo
            
        Returns:
            Agente efímero
        """
        return EphemeralAgent(user_id, language)
    
    @staticmethod
    def get_agent_stats() -> Dict:
        """Obtener estadísticas globales de agentes"""
        return {
            "active_agents": EphemeralAgent._active_agents,
            "total_agents_created": EphemeralAgent._total_agents_created
        }


# ============================================
# DEMOSTRACIÓN - CICLO DE VIDA DEL AGENTE
# ============================================

def demo():
    """
    Demostrar el ciclo de vida del agente efímero
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║   🧠 DEMOSTRACIÓN: AGENTE EFÍMERO                           ║
║   Se crea → Atiende → Se autodestruye                       ║
║   Ideal para 10,000+ usuarios                               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 1. Crear agente
    print("\n📌 PASO 1: Crear agente para usuario...")
    agent1 = AgentFactory.create_agent("user_001", "es")
    
    # 2. Usar agente
    print("\n📌 PASO 2: Usar agente...")
    response = agent1.process_query("¿Qué es una viga?")
    print(f"   Respuesta: {response['response']}")
    
    # 3. Ver estadísticas
    print("\n📌 PASO 3: Ver estadísticas...")
    stats = agent1.get_stats()
    print(f"   {json.dumps(stats, indent=2)}")
    
    # 4. Destruir agente
    print("\n📌 PASO 4: Destruir agente...")
    agent1.destroy()
    
    # 5. Verificar que el agente ya no existe
    print("\n📌 PASO 5: Verificar destrucción...")
    agent1 = None  # Eliminar referencia
    gc.collect()  # Forzar recolección
    
    print(f"\n📊 Agentes activos: {EphemeralAgent._active_agents}")
    
    # 6. Crear múltiples agentes
    print("\n📌 PASO 6: Crear 5 agentes simultáneos...")
    agents = []
    for i in range(5):
        agent = AgentFactory.create_agent(f"user_{i+1:03d}", "es")
        agents.append(agent)
    
    print(f"📊 Agentes activos: {EphemeralAgent._active_agents}")
    
    # 7. Destruir todos
    print("\n📌 PASO 7: Destruir todos los agentes...")
    for agent in agents:
        agent.destroy()
    
    print(f"📊 Agentes activos: {EphemeralAgent._active_agents}")
    print(f"📊 Total agentes creados: {EphemeralAgent._total_agents_created}")

if __name__ == "__main__":
    demo()
