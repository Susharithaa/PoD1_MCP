"""BaseAgent: all worker agents inherit from this."""

from abc import ABC, abstractmethod
from models.agent_session import AgentSession


class BaseAgent(ABC):
    """
    Contract: each agent receives the full session, mutates specific fields,
    and returns the updated session. Raises on unrecoverable error.
    """

    name: str = "base"

    @abstractmethod
    async def run(self, session: AgentSession) -> AgentSession:
        ...
