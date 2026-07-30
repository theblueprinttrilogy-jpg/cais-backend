"""
Base Agent - Abstract Base Class for All CAIS Agents

This module provides the base class for all agents in the CAIS system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all CAIS agents.

    Each agent must implement:
    - analyze(): Main analysis method
    - get_status(): Get agent status
    - log_action(): Log agent actions
    """

    def __init__(self, name: str, agent_type: str):
        """
        Initialize the agent.

        Args:
            name: Agent name
            agent_type: Type of agent
        """
        self.name = name
        self.type = agent_type
        self.status = "initialized"
        self.error = None
        self.last_run = None
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method for the agent.

        Returns:
            dict: Analysis results
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent.

        Returns:
            dict: Status information
        """
        return {
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "error": self.error,
            "last_run": self.last_run,
            "healthy": self.status == "healthy"
        }

    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None):
        """
        Log an agent action.

        Args:
            action: Action name
            details: Additional details
        """
        self.logger.info(f"[{self.name}] {action}" + (f": {details}" if details else ""))

    def set_status(self, status: str, error: Optional[str] = None):
        """
        Set the agent status.

        Args:
            status: New status
            error: Error message if status is 'error'
        """
        self.status = status
        if error:
            self.error = error
        else:
            self.error = None
        self.logger.info(f"[{self.name}] Status: {status}" + (f" - Error: {error}" if error else ""))

    def reset(self):
        """Reset the agent to initial state."""
        self.status = "initialized"
        self.error = None
        self.last_run = None
        self.logger.info(f"[{self.name}] Reset to initial state")

    def reload(self):
        """Reload the agent configuration."""
        self.logger.info(f"[{self.name}] Reloading configuration")
        self.status = "reloaded"

    def clear_cache(self):
        """Clear the agent cache."""
        self.logger.info(f"[{self.name}] Cache cleared")
        self.status = "cache_cleared"

    def is_healthy(self) -> bool:
        """Check if the agent is healthy."""
        return self.status == "healthy"
