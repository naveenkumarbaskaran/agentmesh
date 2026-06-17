from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from agentmesh.event import AgentEvent


class EventStore(ABC):
    @abstractmethod
    async def append(self, event: AgentEvent) -> None: ...
    @abstractmethod
    async def get(self, event_id: str) -> AgentEvent | None: ...
    @abstractmethod
    def replay(self, topic: str, since: float = 0.0,
               until: float | None = None) -> AsyncIterator[AgentEvent]: ...
    @abstractmethod
    async def delete_expired(self) -> int: ...
