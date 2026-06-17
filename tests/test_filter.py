from agentmesh.filter import EventFilter
from agentmesh.event import AgentEvent


def make_event(**kwargs) -> AgentEvent:
    defaults = dict(event_type="order.created", topic="order.created",
                    session_id="s1", run_id="r1", publisher_id="p1",
                    publisher_type="agent", data={}, tenant_id="acme")
    defaults.update(kwargs)
    return AgentEvent(**defaults)


def test_empty_filter_matches_all():
    assert EventFilter({}).matches(make_event())

def test_exact_field_match():
    f = EventFilter({"tenant_id": "acme"})
    assert f.matches(make_event(tenant_id="acme"))
    assert not f.matches(make_event(tenant_id="siemens"))

def test_nested_data_field():
    f = EventFilter({"data.amount": 100})
    assert f.matches(make_event(data={"amount": 100}))
    assert not f.matches(make_event(data={"amount": 50}))

def test_gt_operator():
    f = EventFilter({"data.amount": {"$gt": 1000}})
    assert f.matches(make_event(data={"amount": 1500}))
    assert not f.matches(make_event(data={"amount": 500}))

def test_lt_operator():
    f = EventFilter({"data.amount": {"$lt": 100}})
    assert f.matches(make_event(data={"amount": 50}))
    assert not f.matches(make_event(data={"amount": 200}))

def test_in_operator():
    f = EventFilter({"tenant_id": {"$in": ["acme", "siemens"]}})
    assert f.matches(make_event(tenant_id="acme"))
    assert not f.matches(make_event(tenant_id="unknown"))

def test_multiple_conditions():
    f = EventFilter({"tenant_id": "acme", "data.amount": {"$gt": 100}})
    assert f.matches(make_event(tenant_id="acme", data={"amount": 500}))
    assert not f.matches(make_event(tenant_id="acme", data={"amount": 50}))
