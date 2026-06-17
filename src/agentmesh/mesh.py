from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from agentmesh.dedup import DedupWindow
from agentmesh.dlq import DeadLetterQueue
from agentmesh.event import AgentEvent
from agentmesh.filter import EventFilter
from agentmesh.otel import record_delivered, record_failed, record_published
from agentmesh.router import Router
from agentmesh.store._base import EventStore
from agentmesh.store.jsonl import JsonlStore
from agentmesh.topic import TopicConfig
from agentmesh.transport._base import Transport
from agentmesh.transport.inprocess import InProcessTransport

Handler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class AgentMesh:
    """Agent-native event bus. Zero deps. Pluggable transport and store."""

    def __init__(
        self,
        transport: Transport | None = None,
        store: EventStore | None = None,
        store_path: str = "~/.agentmesh/events.jsonl",
        dedup_window_s: float = 86400.0,
        policy_engine: Any | None = None,
        hook_registry: Any | None = None,
        agent_registry: Any | None = None,
        otel_enabled: bool = True,
    ) -> None:
        self._transport = transport or InProcessTransport()
        self._store = store or JsonlStore(path=store_path)
        self._router = Router()
        self._dedup = DedupWindow(window_s=dedup_window_s)
        self._dlq = DeadLetterQueue()
        self._topics: dict[str, TopicConfig] = {}
        self._paused_queues: dict[str, list[AgentEvent]] = defaultdict(list)
        self._stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"published": 0, "delivered": 0, "failed": 0}
        )
        self._filters: dict[str, list[tuple[Handler, EventFilter]]] = defaultdict(list)
        self._otel = otel_enabled

    async def start(self) -> None:
        await self._transport.start()

    async def close(self) -> None:
        await self._transport.close()

    async def publish(
        self,
        topic: str,
        data: dict[str, Any],
        publisher_id: str,
        session_id: str,
        run_id: str,
        publisher_type: str = "agent",
        event_id: str | None = None,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
        caused_by_event_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        ttl_s: float | None = None,
    ) -> AgentEvent:
        cfg = self._topics.get(topic)
        event = AgentEvent(
            event_id=event_id or str(uuid.uuid4()),
            event_type=topic, topic=topic,
            session_id=session_id, run_id=run_id,
            publisher_id=publisher_id, publisher_type=publisher_type,
            data=data, tenant_id=tenant_id, agent_id=agent_id,
            agent_name=agent_name, caused_by_event_id=caused_by_event_id,
            trace_id=trace_id, span_id=span_id,
            tags=tags or [], metadata=metadata or {},
            ttl_s=ttl_s or (cfg.ttl_s if cfg else None),
        )
        if self._dedup.check_and_mark(event.event_id):
            return event
        await self._store.append(event)
        self._stats[topic]["published"] += 1
        if self._otel:
            record_published(event)
        if cfg and cfg.paused:
            self._paused_queues[topic].append(event)
            return event
        await self._deliver(event)
        return event

    async def _deliver(self, event: AgentEvent) -> None:
        for handler in self._router.get_handlers(event):
            sub_filters = self._filters.get(event.topic, [])
            if any(h is handler and not f.matches(event) for h, f in sub_filters):
                continue
            try:
                await handler(event)
                self._stats[event.topic]["delivered"] += 1
                if self._otel:
                    record_delivered(event, getattr(handler, "__name__", "unknown"))
            except Exception as exc:
                self._stats[event.topic]["failed"] += 1
                cfg = self._topics.get(event.topic)
                if cfg is None or cfg.dlq:
                    self._dlq.push(event, error=str(exc),
                                   subscriber_id=getattr(handler, "__name__", "?"),
                                   config=cfg)
                if self._otel:
                    record_failed(event, str(exc))

    def subscribe(
        self,
        topic: str,
        group: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._router.subscribe(topic, handler, group=group)
            if filter:
                self._filters[topic].append((handler, EventFilter(filter)))
            return handler
        return decorator

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        self._router.unsubscribe(topic, handler)
        self._filters[topic] = [(h, f) for h, f in self._filters[topic] if h is not handler]

    async def request(
        self,
        topic: str,
        data: dict[str, Any],
        publisher_id: str,
        session_id: str,
        run_id: str,
        timeout_s: float = 30.0,
        fallback: Any = None,
    ) -> Any:
        request_id = str(uuid.uuid4())
        fut: asyncio.Future[AgentEvent] = asyncio.get_event_loop().create_future()
        reply_topic = f"_reply.{request_id}"

        @self.subscribe(reply_topic)
        async def _reply(e: AgentEvent) -> None:
            if not fut.done():
                fut.set_result(e)

        await self.publish(topic, {**data, "_request_id": request_id},
                           publisher_id=publisher_id, session_id=session_id, run_id=run_id)
        try:
            return await asyncio.wait_for(fut, timeout=timeout_s)
        except TimeoutError:
            return fallback
        finally:
            self.unsubscribe(reply_topic, _reply)

    async def replay(self, topic: str, since: float = 0.0,
                     until: float | None = None) -> AsyncIterator[AgentEvent]:
        async for event in self._store.replay(topic, since=since, until=until):
            yield event

    def configure_topic(self, topic: str, dlq: bool = True, max_retries: int = 3,
                        retry_backoff_ms: int = 500, ttl_s: float | None = None,
                        delivery_mode: str = "broadcast") -> None:
        self._topics[topic] = TopicConfig(
            topic=topic, dlq=dlq, max_retries=max_retries,
            retry_backoff_ms=retry_backoff_ms, ttl_s=ttl_s, delivery_mode=delivery_mode,
        )

    async def pause(self, topic: str) -> None:
        cfg = self._topics.get(topic, TopicConfig(topic=topic))
        cfg.paused = True
        self._topics[topic] = cfg

    async def resume(self, topic: str) -> None:
        if topic in self._topics:
            self._topics[topic].paused = False
        for event in self._paused_queues.pop(topic, []):
            await self._deliver(event)

    def stats(self) -> dict[str, Any]:
        return {
            "topics": {
                t: {**s, "dlq_depth": self._dlq.depth(t),
                    "subscribers": len(self._router.get_handlers(
                        AgentEvent(event_type=t, topic=t, session_id="", run_id="",
                                   publisher_id="", publisher_type="agent", data={})
                    ))}
                for t, s in self._stats.items()
            }
        }

    async def dlq(self, topic: str) -> AsyncIterator[Any]:
        for dead in self._dlq.iter(topic):
            yield dead

    async def retry(self, dead: Any) -> None:
        await self._deliver(dead.event)
