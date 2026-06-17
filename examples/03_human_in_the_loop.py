"""03 — Human-in-the-loop: agent requests approval, human responds.
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

    @mesh.subscribe("human.approval.requested")
    async def human_reviewer(e: AgentEvent) -> None:
        action = e.data.get("action", "")
        amount = e.data.get("amount", 0)
        request_id = e.data.get("_request_id", "")
        print(f"  [HUMAN] Reviewing: {action} for ${amount:,.2f}")
        await asyncio.sleep(0.05)  # simulate human review time
        await mesh.publish(
            f"_reply.{request_id}",
            data={"approved": True, "approver": "alice@acme.com"},
            publisher_id="alice",
            publisher_type="human",
            session_id=e.session_id,
            run_id=e.run_id,
        )
        print("  [HUMAN] Approved.")

    print("Agent requesting approval for $50,000 wire transfer...")
    response = await mesh.request(
        "human.approval.requested",
        data={"action": "wire_transfer", "amount": 50_000},
        publisher_id="billing-agent",
        session_id="sess-001", run_id="run-001",
        timeout_s=5.0,
        fallback=None,
    )

    if response:
        print(f"\n  Decision: approved={response.data['approved']}")
        print(f"  Approver: {response.data['approver']}")
    else:
        print("\n  Decision: timeout — request denied")

    await mesh.close()


if __name__ == "__main__":
    asyncio.run(main())
