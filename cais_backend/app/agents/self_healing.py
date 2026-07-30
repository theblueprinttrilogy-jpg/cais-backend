"""
Self-Healing System - Automatic Recovery from Failures

This system monitors agents continuously, detects failures,
and applies automatic solutions without human intervention.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 7.3
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services.worm_ledger import WORMService

logger = logging.getLogger(__name__)


class SelfHealingSystem:
    """
    Self-Healing System for CAIS Agents.

    Features:
    - Continuous monitoring of all agents
    - Failure detection
    - Root cause analysis
    - Automatic solution design
    - Healing application
    - WORM Ledger logging
    """

    def __init__(self, worm_service: Optional[WORMService] = None):
        self.agents: Dict[str, Dict] = {}
        self.monitoring_thread: Optional[threading.Thread] = None
        self.is_running: bool = False
        self.health_check_interval: int = 60
        self.failure_threshold: int = 3
        self.worm_service = worm_service

    def register_agent(self, agent_name: str, agent_instance) -> None:
        """Register an agent for monitoring."""
        self.agents[agent_name] = {
            'agent': agent_instance,
            'status': 'healthy',
            'last_check': datetime.now(),
            'failure_count': 0,
            'healing_attempts': 0,
            'history': []
        }
        logger.info(f"Registered agent for self-healing: {agent_name}")

    def start_monitoring(self) -> None:
        """Start the monitoring thread."""
        if self.is_running:
            logger.warning("Self-healing system already running")
            return

        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Self-healing system started")

    def stop_monitoring(self) -> None:
        """Stop the monitoring thread."""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Self-healing system stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            for agent_name in list(self.agents.keys()):
                self._check_agent(agent_name)
            time.sleep(self.health_check_interval)

    def _check_agent(self, agent_name: str) -> None:
        """Check a single agent's health."""
        if agent_name not in self.agents:
            return

        agent_data = self.agents[agent_name]
        agent = agent_data['agent']

        try:
            # Check if agent has a health check method
            is_healthy = True
            if hasattr(agent, 'get_status'):
                status = agent.get_status()
                is_healthy = status.get('healthy', True)
            elif hasattr(agent, 'is_healthy'):
                is_healthy = agent.is_healthy()

            if is_healthy:
                agent_data['status'] = 'healthy'
                agent_data['failure_count'] = 0
                agent_data['last_check'] = datetime.now()
            else:
                agent_data['failure_count'] += 1
                agent_data['last_check'] = datetime.now()

                if agent_data['failure_count'] >= self.failure_threshold:
                    self._heal_agent(agent_name)

        except Exception as e:
            logger.error(f"Error checking agent {agent_name}: {e}")
            agent_data['failure_count'] += 1

            if agent_data['failure_count'] >= self.failure_threshold:
                self._heal_agent(agent_name)

    def _heal_agent(self, agent_name: str) -> None:
        """Apply healing to a failing agent."""
        if agent_name not in self.agents:
            return

        agent_data = self.agents[agent_name]
        logger.warning(f"Starting healing process for agent: {agent_name}")
        agent_data['healing_attempts'] += 1

        try:
            root_cause = self._analyze_root_cause(agent_data)
            blueprint = self._design_solution(root_cause)
            healed = self._apply_healing(agent_data['agent'], blueprint)

            if healed:
                agent_data['status'] = 'healthy'
                agent_data['failure_count'] = 0
                logger.info(f"Agent {agent_name} healed successfully")

                self._log_to_worm('SELF_HEALING_APPLIED', {
                    'agent': agent_name,
                    'root_cause': root_cause,
                    'blueprint': blueprint,
                    'attempts': agent_data['healing_attempts']
                })
            else:
                logger.error(f"Failed to heal agent: {agent_name}")
                agent_data['status'] = 'critical'

        except Exception as e:
            logger.error(f"Error during healing for {agent_name}: {e}")
            agent_data['status'] = 'error'

    def _analyze_root_cause(self, agent_data: Dict[str, Any]) -> str:
        """Analyze root cause of agent failure."""
        status = agent_data.get('status', 'unknown')
        failure_count = agent_data.get('failure_count', 0)

        if failure_count > 10:
            return "Critical failure: Agent crashed repeatedly"
        elif failure_count > 5:
            return "Severe failure: Agent performance degradation"
        else:
            return "Minor failure: Agent recovering from intermittent issues"

    def _design_solution(self, root_cause: str) -> Dict[str, Any]:
        """Design solution for the root cause."""
        solutions = {
            "Critical failure: Agent crashed repeatedly": {
                'action': 'restart_agent',
                'priority': 'high',
                'timeout': 30
            },
            "Severe failure: Agent performance degradation": {
                'action': 'reset_and_reload',
                'priority': 'medium',
                'timeout': 15
            },
            "Minor failure: Agent recovering from intermittent issues": {
                'action': 'clear_cache',
                'priority': 'low',
                'timeout': 5
            }
        }

        return solutions.get(root_cause, {
            'action': 'restart_agent',
            'priority': 'medium',
            'timeout': 10
        })

    def _apply_healing(self, agent, blueprint: Dict[str, Any]) -> bool:
        """Apply healing to the agent."""
        try:
            action = blueprint.get('action', 'restart_agent')

            if action == 'restart_agent':
                if hasattr(agent, 'reset'):
                    agent.reset()
                elif hasattr(agent, 'restart'):
                    agent.restart()
                else:
                    logger.warning(f"Agent has no restart/reset method")
                    return False
                return True

            elif action == 'reset_and_reload':
                if hasattr(agent, 'reset'):
                    agent.reset()
                if hasattr(agent, 'reload'):
                    agent.reload()
                return True

            elif action == 'clear_cache':
                if hasattr(agent, 'clear_cache'):
                    agent.clear_cache()
                return True

            else:
                logger.warning(f"Unknown healing action: {action}")
                return False

        except Exception as e:
            logger.error(f"Error applying healing: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        status = {
            'is_running': self.is_running,
            'total_agents': len(self.agents),
            'healthy': 0,
            'failing': 0,
            'critical': 0,
            'details': {}
        }

        for name, data in self.agents.items():
            agent_status = data.get('status', 'unknown')
            status['details'][name] = {
                'status': agent_status,
                'failure_count': data.get('failure_count', 0),
                'healing_attempts': data.get('healing_attempts', 0),
                'last_check': data.get('last_check', datetime.now()).isoformat()
            }

            if agent_status == 'healthy':
                status['healthy'] += 1
            elif agent_status == 'critical':
                status['critical'] += 1
            else:
                status['failing'] += 1

        return status

    def force_heal(self, agent_name: str) -> bool:
        """Force healing on a specific agent."""
        if agent_name not in self.agents:
            logger.error(f"Agent {agent_name} not found")
            return False

        self._heal_agent(agent_name)
        return True

    def _log_to_worm(self, action: str, data: dict) -> None:
        """Log to WORM Ledger."""
        if self.worm_service:
            try:
                import asyncio
                asyncio.create_task(
                    self.worm_service.add_entry(
                        evidence_gcs_uri=f"self_healing_{datetime.now().timestamp()}",
                        violation_codes={
                            'action': action,
                            'data': data,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to log to WORM Ledger: {e}")
