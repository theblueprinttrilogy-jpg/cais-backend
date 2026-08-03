from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the CAIS backend.
    Agents implement the execute method to perform their primary function.
    """

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's primary logic with the given input.

        :param input_data: Dictionary containing input parameters for the agent.
        :return: Dictionary containing the result of the execution.
        """
        pass

    async def initialize(self) -> None:
        """
        Optional asynchronous initialization routine for the agent.
        This method is called by the orchestrator during startup.
        By default, it does nothing; subclasses may override it.
        """
        pass

    async def shutdown(self) -> None:
        """
        Optional asynchronous cleanup routine for the agent.
        This method is called by the orchestrator during shutdown.
        By default, it does nothing; subclasses may override it.
        """
        pass
