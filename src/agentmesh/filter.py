from __future__ import annotations

from typing import Any

from agentmesh.event import AgentEvent


def _get_nested(obj: Any, path: str) -> Any:
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current


def _matches_condition(actual: Any, condition: Any) -> bool:
    if isinstance(condition, dict):
        for op, value in condition.items():
            if op == "$gt" and (actual is None or actual <= value):
                return False
            elif op == "$lt" and (actual is None or actual >= value):
                return False
            elif op == "$gte" and (actual is None or actual < value):
                return False
            elif op == "$lte" and (actual is None or actual > value):
                return False
            elif op == "$in" and actual not in value:
                return False
            elif op == "$ne" and actual == value:
                return False
        return True
    return actual == condition


class EventFilter:
    def __init__(self, conditions: dict[str, Any]) -> None:
        self._conditions = conditions

    def matches(self, event: AgentEvent) -> bool:
        if not self._conditions:
            return True
        event_dict = event.to_dict()
        for path, condition in self._conditions.items():
            if not _matches_condition(_get_nested(event_dict, path), condition):
                return False
        return True
