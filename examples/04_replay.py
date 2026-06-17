"""04 — Event replay: recover missed events from the persistent store.
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

    # Session 1: publish 5 events
    mesh = AgentMesh(store_path=store_path)
    await mesh.start()
    print("Publishing 5 order events...")
    for i in range(5):
        await mesh.publish(
            "order.created",
            data={"order_id": f"ORD-{i:03d}", "seq": i},
            publisher_id="shop-agent",
            session_id="sess-001", run_id=f"r{i}", tenant_id="acme",
        )
    await asyncio.sleep(0.05)
    await mesh.close()

    # Session 2: new instance, replay everything
    print("\nNew mesh instance — replaying from persistent store...")
    mesh2 = AgentMesh(store_path=store_path)
    await mesh2.start()

    count = 0
    async for event in mesh2.replay("order.created"):
        print(f"  replayed: {event.data['order_id']}  seq={event.data['seq']}")
        count += 1

    print(f"\nReplayed {count} events. Full history preserved across restarts.")
    await mesh2.close()


if __name__ == "__main__":
    asyncio.run(main())
