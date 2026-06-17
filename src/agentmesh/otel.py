from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from agentmesh.event import AgentEvent

try:
    from opentelemetry import metrics as _otel_metrics
    from opentelemetry import trace as _otel_trace
    _tracer = _otel_trace.get_tracer("agentmesh", "0.1.0")
    _meter = _otel_metrics.get_meter("agentmesh", "0.1.0")
    _events_published = _meter.create_counter("agentmesh.events.published")
    _events_delivered = _meter.create_counter("agentmesh.events.delivered")
    _events_failed = _meter.create_counter("agentmesh.events.failed")
    _delivery_latency = _meter.create_histogram("agentmesh.delivery.latency_ms", unit="ms")
    _OTEL = True
except ImportError:
    _OTEL = False


def record_published(event: AgentEvent) -> None:
    if not _OTEL:
        return
    _events_published.add(1, {"topic": event.topic, "tenant_id": event.tenant_id or "",  # type: ignore
                               "publisher_type": event.publisher_type})


def record_delivered(event: AgentEvent, subscriber_id: str) -> None:
    if not _OTEL:
        return
    _events_delivered.add(1, {"topic": event.topic, "tenant_id": event.tenant_id or "",  # type: ignore
                               "subscriber_id": subscriber_id})


def record_failed(event: AgentEvent, error: str) -> None:
    if not _OTEL:
        return
    _events_failed.add(1, {"topic": event.topic, "tenant_id": event.tenant_id or "",  # type: ignore
                            "error": error[:50]})


@contextmanager
def event_span(event: AgentEvent) -> Generator[Any, None, None]:
    if not _OTEL:
        yield None
        return
    with _tracer.start_as_current_span(f"agentmesh.publish {event.topic}") as span:  # type: ignore
        span.set_attribute("agentmesh.topic", event.topic)
        span.set_attribute("agentmesh.event_type", event.event_type)
        span.set_attribute("agentmesh.tenant_id", event.tenant_id or "")
        span.set_attribute("agentmesh.publisher_type", event.publisher_type)
        yield span
