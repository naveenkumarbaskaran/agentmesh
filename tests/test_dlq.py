import pytest
from agentmesh.dlq import DeadLetterQueue, DeadEvent
from agentmesh.event import AgentEvent
from agentmesh.topic import TopicConfig


def make_event(topic: str = "order.created") -> AgentEvent:
    return AgentEvent(event_type=topic, topic=topic, session_id="s1", run_id="r1",
                      publisher_id="p1", publisher_type="agent", data={})


def test_push_to_dlq():
    dlq = DeadLetterQueue()
    dlq.push(make_event(), error="failed", subscriber_id="sub-1")
    assert dlq.depth("order.created") == 1


def test_pop_from_dlq():
    dlq = DeadLetterQueue()
    e = make_event()
    dlq.push(e, error="failed", subscriber_id="sub-1")
    dead = dlq.pop("order.created")
    assert dead is not None
    assert dead.event.event_id == e.event_id
    assert dead.error == "failed"
    assert dead.attempts == 1
    assert dlq.depth("order.created") == 0


def test_pop_empty_returns_none():
    assert DeadLetterQueue().pop("nonexistent") is None


def test_max_retries_respected():
    config = TopicConfig(topic="order.created", max_retries=2)
    dlq = DeadLetterQueue()
    e = make_event()
    dlq.push(e, error="fail 1", subscriber_id="sub-1")
    dead = dlq.pop("order.created")
    dlq.push(dead.event, error="fail 2", subscriber_id="sub-1", previous_attempts=dead.attempts)
    dead2 = dlq.pop("order.created")
    assert dead2.attempts == 2
    should_retry = dlq.push(dead2.event, error="fail 3", subscriber_id="sub-1",
                            previous_attempts=dead2.attempts, config=config)
    assert not should_retry
    assert dlq.depth("order.created") == 0


def test_iterate_dlq():
    dlq = DeadLetterQueue()
    for i in range(3):
        dlq.push(make_event(), error=f"err{i}", subscriber_id="sub-1")
    assert len(list(dlq.iter("order.created"))) == 3
