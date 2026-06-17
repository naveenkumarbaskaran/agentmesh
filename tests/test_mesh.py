import asyncio

import pytest

from agentmesh.event import AgentEvent
from agentmesh.mesh import AgentMesh


@pytest.fixture
async def mesh(tmp_path):
    m = AgentMesh(store_path=str(tmp_path / "events.jsonl"))
    await m.start()
    yield m
    await m.close()


@pytest.mark.asyncio
async def test_publish_and_subscribe(mesh):
    received = []
    @mesh.subscribe("order.created")
    async def handler(e: AgentEvent) -> None:
        received.append(e)
    await mesh.publish("order.created", data={"order_id": "ORD-001"},
                       publisher_id="agent-1", session_id="s1", run_id="r1")
    await asyncio.sleep(0.1)
    assert len(received) == 1
    assert received[0].data["order_id"] == "ORD-001"


@pytest.mark.asyncio
async def test_wildcard_subscription(mesh):
    received = []
    @mesh.subscribe("order.*")
    async def handler(e: AgentEvent) -> None:
        received.append(e.event_type)
    await mesh.publish("order.created", data={}, publisher_id="p1", session_id="s1", run_id="r1")
    await mesh.publish("order.updated", data={}, publisher_id="p1", session_id="s1", run_id="r2")
    await asyncio.sleep(0.1)
    assert "order.created" in received
    assert "order.updated" in received


@pytest.mark.asyncio
async def test_deduplication(mesh):
    received = []
    @mesh.subscribe("order.created")
    async def handler(e: AgentEvent) -> None:
        received.append(e)
    await mesh.publish("order.created", data={}, publisher_id="p1", session_id="s1",
                       run_id="r1", event_id="dup-evt-001")
    await mesh.publish("order.created", data={}, publisher_id="p1", session_id="s1",
                       run_id="r1", event_id="dup-evt-001")
    await asyncio.sleep(0.1)
    assert len(received) == 1


@pytest.mark.asyncio
async def test_tenant_isolation(mesh):
    acme, siemens = [], []
    @mesh.subscribe("acme:order.created")
    async def acme_h(e: AgentEvent) -> None: acme.append(e)
    @mesh.subscribe("siemens:order.created")
    async def siemens_h(e: AgentEvent) -> None: siemens.append(e)
    await mesh.publish("acme:order.created", data={}, publisher_id="p1",
                       session_id="s1", run_id="r1", tenant_id="acme")
    await asyncio.sleep(0.1)
    assert len(acme) == 1 and len(siemens) == 0


@pytest.mark.asyncio
async def test_consumer_group_exclusive(mesh):
    calls = []
    @mesh.subscribe("order.created", group="workers")
    async def w1(e: AgentEvent) -> None: calls.append("w1")
    @mesh.subscribe("order.created", group="workers")
    async def w2(e: AgentEvent) -> None: calls.append("w2")
    await mesh.publish("order.created", data={}, publisher_id="p1", session_id="s1", run_id="r1")
    await asyncio.sleep(0.1)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_topic_pause_resume(mesh):
    received = []
    @mesh.subscribe("order.created")
    async def handler(e: AgentEvent) -> None: received.append(e)
    await mesh.pause("order.created")
    await mesh.publish("order.created", data={}, publisher_id="p1", session_id="s1", run_id="r1")
    await asyncio.sleep(0.1)
    assert len(received) == 0
    await mesh.resume("order.created")
    await asyncio.sleep(0.1)
    assert len(received) == 1


@pytest.mark.asyncio
async def test_replay(tmp_path):
    m = AgentMesh(store_path=str(tmp_path / "events.jsonl"))
    await m.start()
    await m.publish("order.created", data={"n": 1}, publisher_id="p1", session_id="s1", run_id="r1")
    await m.publish("order.created", data={"n": 2}, publisher_id="p1", session_id="s1", run_id="r2")
    await asyncio.sleep(0.05)
    replayed = [e async for e in m.replay("order.created")]
    assert len(replayed) == 2
    await m.close()


@pytest.mark.asyncio
async def test_stats(mesh):
    await mesh.publish("order.created", data={}, publisher_id="p1", session_id="s1", run_id="r1")
    await asyncio.sleep(0.05)
    stats = mesh.stats()
    assert "order.created" in stats["topics"]
    assert stats["topics"]["order.created"]["published"] >= 1
