"""01 — Hello AgentMesh. Simplest possible example.
pip install agentmesh-py && python main.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from agentmesh import AgentMesh, AgentEvent  # noqa: E402


async def main() -> None:
    mesh = AgentMesh()
    await mesh.start()

    @mesh.subscribe("order.created")
    async def handle_order(e: AgentEvent) -> None:
        print(f"  [subscriber] order={e.data['order_id']} tenant={e.tenant_id}")

    print("Publishing order.created...")
    await mesh.publish(
        "order.created",
        data={"order_id": "ORD-001", "amount": 299.99},
        publisher_id="billing-agent",
        session_id="sess-001", run_id="run-001",
        tenant_id="acme",
    )
    await asyncio.sleep(0.1)
    print(f"Stats: {mesh.stats()}")
    await mesh.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
