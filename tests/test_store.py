import asyncio
import time
import pytest
from agentmesh.event import AgentEvent
from agentmesh.store.jsonl import JsonlStore


def make_event(topic: str = "order.created", **kwargs) -> AgentEvent:
    return AgentEvent(event_type=topic, topic=topic, session_id="s1", run_id="r1",
                      publisher_id="p1", publisher_type="agent", data={}, **kwargs)


@pytest.fixture
def store(tmp_path):
    return JsonlStore(path=str(tmp_path / "events.jsonl"))


@pytest.mark.asyncio
async def test_append_and_replay(store):
    e = make_event()
    await store.append(e)
    events = [ev async for ev in store.replay("order.created")]
    assert len(events) == 1
    assert events[0].event_id == e.event_id


@pytest.mark.asyncio
async def test_replay_multiple_topics(store):
    await store.append(make_event("order.created"))
    await store.append(make_event("payment.initiated"))
    await store.append(make_event("order.created"))
    events = [ev async for ev in store.replay("order.created")]
    assert len(events) == 2


@pytest.mark.asyncio
async def test_replay_since(store):
    e1 = make_event()
    await store.append(e1)
    t_mid = time.time()
    await asyncio.sleep(0.01)
    e2 = make_event()
    await store.append(e2)
    events = [ev async for ev in store.replay("order.created", since=t_mid)]
    assert len(events) == 1
    assert events[0].event_id == e2.event_id


@pytest.mark.asyncio
async def test_get_by_id(store):
    e = make_event()
    await store.append(e)
    found = await store.get(e.event_id)
    assert found is not None and found.event_id == e.event_id


@pytest.mark.asyncio
async def test_get_missing_returns_none(store):
    assert await store.get("nonexistent") is None


@pytest.mark.asyncio
async def test_expired_events_pruned(store):
    e = make_event(ttl_s=0.01)
    await store.append(e)
    await asyncio.sleep(0.02)
    removed = await store.delete_expired()
    assert removed >= 1
