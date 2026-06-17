from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path

from agentmesh.event import AgentEvent
from agentmesh.store._base import EventStore


class JsonlStore(EventStore):
    def __init__(self, path: str = "~/.agentmesh/events.jsonl") -> None:
        self._path = Path(os.path.expanduser(path))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def append(self, event: AgentEvent) -> None:
        line = json.dumps(event.to_dict(), default=str)
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._write_line, line)

    def _write_line(self, line: str) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def get(self, event_id: str) -> AgentEvent | None:
        if not self._path.exists():
            return None
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    d = json.loads(line)
                    if d.get("event_id") == event_id:
                        return AgentEvent.from_dict(d)
                except json.JSONDecodeError:
                    continue
        return None

    async def replay(self, topic: str, since: float = 0.0,  # type: ignore[override]
                     until: float | None = None) -> AsyncIterator[AgentEvent]:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("topic") != topic:
                continue
            ts = d.get("timestamp", 0.0)
            if ts < since:
                continue
            if until is not None and ts > until:
                continue
            yield AgentEvent.from_dict(d)

    async def delete_expired(self) -> int:
        if not self._path.exists():
            return 0
        now = time.time()
        kept, removed = [], 0
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                ttl = d.get("ttl_s")
                if ttl is not None and (now - d.get("timestamp", 0.0)) > ttl:
                    removed += 1
                    continue
            except json.JSONDecodeError:
                pass
            kept.append(line)
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._rewrite, kept)
        return removed

    def _rewrite(self, lines: list[str]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
