from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Iterator
from dataclasses import dataclass, field

from agentmesh.event import AgentEvent
from agentmesh.topic import TopicConfig


@dataclass
class DeadEvent:
    event: AgentEvent
    error: str
    attempts: int
    subscriber_id: str
    last_attempt_at: float = field(default_factory=time.time)


class DeadLetterQueue:
    def __init__(self) -> None:
        self._queues: dict[str, deque[DeadEvent]] = defaultdict(deque)

    def push(self, event: AgentEvent, error: str, subscriber_id: str,
             previous_attempts: int = 0, config: TopicConfig | None = None) -> bool:
        attempts = previous_attempts + 1
        if config is not None and attempts > config.max_retries:
            return False
        self._queues[event.topic].append(
            DeadEvent(event=event, error=error, attempts=attempts, subscriber_id=subscriber_id)
        )
        return True

    def pop(self, topic: str) -> DeadEvent | None:
        q = self._queues.get(topic)
        return q.popleft() if q else None

    def depth(self, topic: str) -> int:
        return len(self._queues.get(topic, []))

    def iter(self, topic: str) -> Iterator[DeadEvent]:
        yield from list(self._queues.get(topic, []))
