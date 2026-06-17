import pytest
from agentmesh.router import Router
from agentmesh.event import AgentEvent


def make_event(topic: str, **kwargs) -> AgentEvent:
    return AgentEvent(event_type=topic, topic=topic, session_id="s1", run_id="r1",
                      publisher_id="p1", publisher_type="agent", data={}, **kwargs)


def test_exact_match():
    r = Router()
    assert r.matches("order.created", "order.created")
    assert not r.matches("order.created", "order.updated")


def test_wildcard_single_segment():
    r = Router()
    assert r.matches("order.*", "order.created")
    assert r.matches("order.*", "order.updated")
    assert not r.matches("order.*", "order.item.created")


def test_wildcard_multi_segment():
    r = Router()
    assert r.matches("order.>", "order.created")
    assert r.matches("order.>", "order.item.created")
    assert r.matches("order.>", "order.item.variant.updated")
    assert not r.matches("order.>", "payment.created")


def test_wildcard_any_category():
    r = Router()
    assert r.matches("*.created", "order.created")
    assert r.matches("*.created", "payment.created")
    assert not r.matches("*.created", "order.updated")


def test_wildcard_all():
    r = Router()
    assert r.matches(">", "order.created")
    assert r.matches(">", "system.heartbeat")
    assert r.matches(">", "a.b.c.d.e")


def test_tenant_namespaced_topic():
    r = Router()
    assert r.matches("acme:order.created", "acme:order.created")
    assert not r.matches("acme:order.created", "siemens:order.created")
    assert r.matches("acme:>", "acme:order.created")
    assert not r.matches("acme:>", "siemens:order.created")


@pytest.mark.asyncio
async def test_get_handlers_broadcast():
    r = Router()
    calls = []
    async def h1(e): calls.append("h1")
    async def h2(e): calls.append("h2")
    r.subscribe("order.created", h1)
    r.subscribe("order.created", h2)
    event = make_event("order.created")
    handlers = r.get_handlers(event)
    for h in handlers:
        await h(event)
    assert calls == ["h1", "h2"]


@pytest.mark.asyncio
async def test_get_handlers_consumer_group():
    r = Router()
    calls = []
    async def h1(e): calls.append("h1")
    async def h2(e): calls.append("h2")
    r.subscribe("order.created", h1, group="workers")
    r.subscribe("order.created", h2, group="workers")
    event = make_event("order.created")
    handlers = r.get_handlers(event)
    for h in handlers:
        await h(event)
    assert len(calls) == 1


def test_unsubscribe():
    r = Router()
    async def h(e): pass
    r.subscribe("order.created", h)
    r.unsubscribe("order.created", h)
    event = make_event("order.created")
    assert len(r.get_handlers(event)) == 0
