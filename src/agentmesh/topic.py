from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TopicConfig:
    topic:            str
    dlq:              bool = True
    max_retries:      int = 3
    retry_backoff_ms: int = 500
    ttl_s:            float | None = None
    delivery_mode:    str = "broadcast"
    paused:           bool = False
