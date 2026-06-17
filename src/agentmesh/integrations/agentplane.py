from __future__ import annotations

from typing import Any

from agentmesh.event import AgentEvent


async def check_publish_policy(engine: Any, event: AgentEvent) -> bool:
    try:
        from agentplane import PolicyContext
        ctx = PolicyContext.new(
            agent_id=event.publisher_id, tenant_id=event.tenant_id,
            hookpoint="before_publish", tool_name=event.topic, tool_inputs=event.data,
        )
        await engine.evaluate(ctx)
        return True
    except Exception:
        return False


async def check_deliver_policy(engine: Any, event: AgentEvent, subscriber_id: str) -> bool:
    try:
        from agentplane import PolicyContext
        ctx = PolicyContext.new(
            agent_id=subscriber_id, tenant_id=event.tenant_id,
            hookpoint="before_deliver", tool_name=event.topic,
        )
        await engine.evaluate(ctx)
        return True
    except Exception:
        return False
