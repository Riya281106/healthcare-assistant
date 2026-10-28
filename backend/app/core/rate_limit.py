"""
Tiny in-memory sliding-window rate limiter (per process).

Purpose: stop one account from burning the LLM quota / API budget.
Not a substitute for a real gateway limiter if you ever run several
server processes -- each process keeps its own counts.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            calls = self._calls[key]
            while calls and now - calls[0] > self.window:
                calls.popleft()
            if len(calls) >= self.max_calls:
                return False
            calls.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()
