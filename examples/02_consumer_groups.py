"""02 — Consumer groups: only one worker processes each event.
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
    processed: list[tuple[str, float]] = []

    @mesh.subscribe("payment.initiated", group="payment-workers")
    async def worker_1(e: AgentEvent) -> None:
        processed.append(("worker-1", e.data["amount"]))
        print(f"  worker-1 processed ${e.data['amount']:.2f}")

    @mesh.subscribe("payment.initiated", group="payment-workers")
    async def worker_2(e: AgentEvent) -> None:
        processed.append(("worker-2", e.data["amount"]))
        print(f"  worker-2 processed ${e.data['amount']:.2f}")

    print("Publishing 4 payment events to group 'payment-workers'...")
    for i, amount in enumerate([100.0, 200.0, 300.0, 400.0]):
        await mesh.publish("payment.initiated",
                           data={"payment_id": f"PAY-{i:03d}", "amount": amount},
                           publisher_id="billing-agent",
                           session_id="s1", run_id=f"r{i}", tenant_id="acme")

    await asyncio.sleep(0.1)
    workers = [w for w, _ in processed]
    print(f"\nProcessed by: {workers}")
    print(f"Each event handled by exactly one worker: {len(processed) == 4}")
    await mesh.close()


if __name__ == "__main__":
    asyncio.run(main())
