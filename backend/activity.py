"""
Activity Log — in-memory record of real system events (queries, ingests)
for the Dashboard live feed and query counter.
"""

import time
from collections import deque
from threading import Lock

_events: deque = deque(maxlen=100)
_query_count = 0
_lock = Lock()


def log_event(kind: str, message: str):
    global _query_count
    with _lock:
        _events.append({"ts": time.time(), "kind": kind, "message": message})
        if kind == "QUERY":
            _query_count += 1


def get_activity() -> dict:
    with _lock:
        return {
            "events": list(_events)[-30:],
            "query_count": _query_count,
        }
