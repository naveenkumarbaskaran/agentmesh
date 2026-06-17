from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from agentmesh.event import AgentEvent
from agentmesh.transport._base import Transport

Handler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class InProcessTransport(Transport):
    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[str | None, Handler]]] = {}
        self._queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.ensure_future(self._dispatch_loop())

    async def close(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def publish(self, topic: str, event: AgentEvent) -> None:
        await self._queue.put(event)

    async def subscribe(self, topic: str, group: str | None, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append((group, handler))

    async def unsubscribe(self, topic: str, handler: Handler) -> None:
        if topic in self._handlers:
            self._handlers[topic] = [(g, h) for g, h in self._handlers[topic] if h is not handler]

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self._deliver(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _deliver(self, event: AgentEvent) -> None:
        for _group, handler in self._handlers.get(event.topic, []):
            try:
                await handler(event)
            except Exception:
                pass
