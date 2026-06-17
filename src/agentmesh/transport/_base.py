from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from agentmesh.event import AgentEvent

Handler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class Transport(ABC):
    @abstractmethod
    async def publish(self, topic: str, event: AgentEvent) -> None: ...
    @abstractmethod
    async def subscribe(self, topic: str, group: str | None, handler: Handler) -> None: ...
    @abstractmethod
    async def unsubscribe(self, topic: str, handler: Handler) -> None: ...
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def close(self) -> None: ...
