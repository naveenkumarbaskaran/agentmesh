from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from agentmesh.event import AgentEvent

Handler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    if pattern == ">":
        return re.compile(r".+")
    result = []
    i = 0
    while i < len(pattern):
        if pattern[i] == ">":
            result.append(r"[^:]+(?:\.[^:]+)*")
            i += 1
        elif pattern[i] == "*":
            result.append(r"[^.:]+")
            i += 1
        else:
            j = i
            while j < len(pattern) and pattern[j] not in (">", "*"):
                j += 1
            result.append(re.escape(pattern[i:j]))
            i = j
    return re.compile("^" + "".join(result) + "$")


class _Subscription:
    def __init__(self, pattern: str, handler: Handler, group: str | None) -> None:
        self.pattern = pattern
        self.handler = handler
        self.group = group
        self._regex = _pattern_to_regex(pattern)

    def matches(self, topic: str) -> bool:
        return bool(self._regex.match(topic))


class Router:
    def __init__(self) -> None:
        self._subs: list[_Subscription] = []
        self._group_counters: dict[str, int] = defaultdict(int)

    def subscribe(self, pattern: str, handler: Handler, group: str | None = None) -> None:
        self._subs.append(_Subscription(pattern, handler, group))

    def unsubscribe(self, pattern: str, handler: Handler) -> None:
        self._subs = [s for s in self._subs
                      if not (s.pattern == pattern and s.handler is handler)]

    def matches(self, pattern: str, topic: str) -> bool:
        return bool(_pattern_to_regex(pattern).match(topic))

    def get_handlers(self, event: AgentEvent) -> list[Handler]:
        matched = [s for s in self._subs if s.matches(event.topic)]
        handlers: list[Handler] = []
        seen_groups: dict[str, bool] = {}
        for sub in matched:
            if sub.group is None:
                handlers.append(sub.handler)
            elif sub.group not in seen_groups:
                group_subs = [s for s in matched if s.group == sub.group]
                idx = self._group_counters[sub.group] % len(group_subs)
                self._group_counters[sub.group] += 1
                handlers.append(group_subs[idx].handler)
                seen_groups[sub.group] = True
        return handlers
