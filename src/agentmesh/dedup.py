from __future__ import annotations
import time


class DedupWindow:
    def __init__(self, window_s: float = 86400.0) -> None:
        self._window_s = window_s
        self._seen: dict[str, float] = {}

    def is_duplicate(self, event_id: str) -> bool:
        seen_at = self._seen.get(event_id)
        if seen_at is None:
            return False
        if (time.time() - seen_at) > self._window_s:
            del self._seen[event_id]
            return False
        return True

    def mark_seen(self, event_id: str) -> None:
        self._seen[event_id] = time.time()

    def check_and_mark(self, event_id: str) -> bool:
        if self.is_duplicate(event_id):
            return True
        self.mark_seen(event_id)
        return False

    def gc(self) -> int:
        now = time.time()
        expired = [k for k, v in self._seen.items() if (now - v) > self._window_s]
        for k in expired:
            del self._seen[k]
        return len(expired)
