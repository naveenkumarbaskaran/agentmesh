"""05 — Multi-agent workflow: order → inventory → billing → notification.
Each agent reacts to events from the previous stage.
pip install agentmesh-py && python main.py
"""
import asyncio
import tempfile
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from agentmesh import AgentMesh, AgentEvent  # noqa: E402


async def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    mesh = AgentMesh(store_path=store_path)
    await mesh.start()

    log: list[str] = []

    @mesh.subscribe("order.created")
    async def inventory_agent(e: AgentEvent) -> None:
        log.append(f"inventory  → reserved stock for {e.data['order_id']}")
        await mesh.publish(
            "inventory.reserved",
            data={**e.data, "reserved": True},
            publisher_id="inventory-agent",
            session_id=e.session_id, run_id=e.run_id,
            caused_by_event_id=e.event_id, tenant_id=e.tenant_id,
        )

    @mesh.subscribe("inventory.reserved")
    async def billing_agent(e: AgentEvent) -> None:
        log.append(f"billing    → charged ${e.data.get('amount', 0):.2f} for {e.data['order_id']}")
        await mesh.publish(
            "payment.charged",
            data={**e.data, "charged": True},
            publisher_id="billing-agent",
            session_id=e.session_id, run_id=e.run_id,
            caused_by_event_id=e.event_id, tenant_id=e.tenant_id,
        )

    @mesh.subscribe("payment.charged")
    async def notification_agent(e: AgentEvent) -> None:
        log.append(f"notification → emailed customer for {e.data['order_id']}")

    print("Triggering 3-agent workflow with order.created...\n")
    await mesh.publish(
        "order.created",
        data={"order_id": "ORD-999", "amount": 149.99},
        publisher_id="shop-agent",
        session_id="sess-001", run_id="run-001", tenant_id="acme",
    )
    await asyncio.sleep(0.3)

    print("Workflow execution log:")
    for step in log:
        print(f"  ✓ {step}")

    stats = mesh.stats()["topics"]
    print(f"\nEvents published: {sum(v['published'] for v in stats.values())}")
    print(f"Events delivered: {sum(v['delivered'] for v in stats.values())}")
    await mesh.close()


if __name__ == "__main__":
    asyncio.run(main())
