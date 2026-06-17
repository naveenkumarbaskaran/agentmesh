from __future__ import annotations

from typing import Any


def register_mesh_hooks(mesh: Any, registry: Any) -> None:
    try:
        from agenthooks import hookpoint
    except ImportError:
        return
    mesh._hp_before_publish = hookpoint("agentmesh.before_publish", registries=[registry])
    mesh._hp_after_publish  = hookpoint("agentmesh.after_publish",  registries=[registry])
    mesh._hp_before_deliver = hookpoint("agentmesh.before_deliver", registries=[registry])
    mesh._hp_after_deliver  = hookpoint("agentmesh.after_deliver",  registries=[registry])
