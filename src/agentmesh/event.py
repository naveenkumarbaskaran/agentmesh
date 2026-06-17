from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentEvent:
    event_type:         str
    topic:              str
    session_id:         str
    run_id:             str
    publisher_id:       str
    publisher_type:     str
    data:               dict[str, Any]
    event_id:           str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:          float = field(default_factory=time.time)
    schema_version:     str = "1.0"
    parent_run_id:      str | None = None
    caused_by_event_id: str | None = None
    trace_id:           str | None = None
    span_id:            str | None = None
    agent_id:           str | None = None
    agent_name:         str | None = None
    tenant_id:          str | None = None
    provider:           str | None = None
    delivery_mode:      str = "broadcast"
    ttl_s:              float | None = None
    tags:               list[str] = field(default_factory=list)
    metadata:           dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "event_type": self.event_type,
            "topic": self.topic, "schema_version": self.schema_version,
            "timestamp": self.timestamp, "session_id": self.session_id,
            "run_id": self.run_id, "parent_run_id": self.parent_run_id,
            "caused_by_event_id": self.caused_by_event_id,
            "trace_id": self.trace_id, "span_id": self.span_id,
            "agent_id": self.agent_id, "agent_name": self.agent_name,
            "tenant_id": self.tenant_id, "publisher_id": self.publisher_id,
            "publisher_type": self.publisher_type, "provider": self.provider,
            "delivery_mode": self.delivery_mode, "ttl_s": self.ttl_s,
            "tags": self.tags, "metadata": self.metadata, "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentEvent:
        return cls(
            event_id=d["event_id"], event_type=d["event_type"],
            topic=d["topic"], schema_version=d.get("schema_version", "1.0"),
            timestamp=d["timestamp"], session_id=d["session_id"],
            run_id=d["run_id"], parent_run_id=d.get("parent_run_id"),
            caused_by_event_id=d.get("caused_by_event_id"),
            trace_id=d.get("trace_id"), span_id=d.get("span_id"),
            agent_id=d.get("agent_id"), agent_name=d.get("agent_name"),
            tenant_id=d.get("tenant_id"), publisher_id=d["publisher_id"],
            publisher_type=d["publisher_type"], provider=d.get("provider"),
            delivery_mode=d.get("delivery_mode", "broadcast"),
            ttl_s=d.get("ttl_s"), tags=d.get("tags", []),
            metadata=d.get("metadata", {}), data=d.get("data", {}),
        )

    def is_expired(self) -> bool:
        if self.ttl_s is None:
            return False
        return (time.time() - self.timestamp) > self.ttl_s
