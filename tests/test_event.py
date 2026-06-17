import time
import uuid
from agentmesh.event import AgentEvent


def test_event_required_fields():
    e = AgentEvent(
        event_type="order.created", topic="order.created",
        session_id="s1", run_id="r1", publisher_id="agent-1",
        publisher_type="agent", data={"order_id": "ORD-001"},
    )
    assert e.event_type == "order.created"
    assert e.schema_version == "1.0"
    assert e.delivery_mode == "broadcast"
    assert e.tags == []
    assert e.metadata == {}
    assert e.ttl_s is None
    assert e.tenant_id is None
    assert e.caused_by_event_id is None


def test_event_id_auto_generated():
    e = AgentEvent(event_type="t", topic="t", session_id="s",
                   run_id="r", publisher_id="p", publisher_type="agent", data={})
    assert len(e.event_id) == 36


def test_event_id_custom():
    custom_id = str(uuid.uuid4())
    e = AgentEvent(event_type="t", topic="t", session_id="s",
                   run_id="r", publisher_id="p", publisher_type="agent",
                   data={}, event_id=custom_id)
    assert e.event_id == custom_id


def test_event_timestamp_auto():
    before = time.time()
    e = AgentEvent(event_type="t", topic="t", session_id="s",
                   run_id="r", publisher_id="p", publisher_type="agent", data={})
    after = time.time()
    assert before <= e.timestamp <= after


def test_event_to_dict():
    e = AgentEvent(event_type="order.created", topic="order.created",
                   session_id="s1", run_id="r1", publisher_id="agent-1",
                   publisher_type="agent", data={"amount": 99.99}, tenant_id="acme")
    d = e.to_dict()
    assert d["event_type"] == "order.created"
    assert d["tenant_id"] == "acme"
    assert d["data"]["amount"] == 99.99


def test_event_from_dict():
    e = AgentEvent(event_type="order.created", topic="order.created",
                   session_id="s1", run_id="r1", publisher_id="agent-1",
                   publisher_type="agent", data={"amount": 99.99})
    d = e.to_dict()
    e2 = AgentEvent.from_dict(d)
    assert e2.event_id == e.event_id
    assert e2.event_type == e.event_type
    assert e2.data == e.data


def test_event_is_expired_no_ttl():
    e = AgentEvent(event_type="t", topic="t", session_id="s",
                   run_id="r", publisher_id="p", publisher_type="agent", data={})
    assert not e.is_expired()


def test_event_is_expired_with_ttl():
    e = AgentEvent(event_type="t", topic="t", session_id="s",
                   run_id="r", publisher_id="p", publisher_type="agent",
                   data={}, ttl_s=0.001, timestamp=time.time() - 1.0)
    assert e.is_expired()
