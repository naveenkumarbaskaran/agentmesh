import time
from agentmesh.dedup import DedupWindow


def test_first_event_not_duplicate():
    d = DedupWindow(window_s=60.0)
    assert not d.is_duplicate("evt-001")

def test_same_event_id_is_duplicate():
    d = DedupWindow(window_s=60.0)
    d.mark_seen("evt-001")
    assert d.is_duplicate("evt-001")

def test_different_event_id_not_duplicate():
    d = DedupWindow(window_s=60.0)
    d.mark_seen("evt-001")
    assert not d.is_duplicate("evt-002")

def test_expired_event_not_duplicate():
    d = DedupWindow(window_s=0.01)
    d.mark_seen("evt-001")
    time.sleep(0.02)
    d.gc()
    assert not d.is_duplicate("evt-001")

def test_check_and_mark():
    d = DedupWindow(window_s=60.0)
    assert not d.check_and_mark("evt-001")
    assert d.check_and_mark("evt-001")
