"""A small in-process cache with a time limit, for results that are costly to
compute and fine to show a minute old."""

import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import TypeVar

T = TypeVar("T")


class TTLCache:
    """When an entry expires, the first request to ask recomputes it while any
    others arriving meanwhile get the previous value, so an expiry costs one
    query rather than one per waiting dashboard."""

    def __init__(self, *, ttl_seconds: float, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[Hashable, tuple[float, object]] = OrderedDict()
        self._refreshing: set[Hashable] = set()
        self._lock = threading.Lock()

    def get_or_compute(self, key: Hashable, compute: Callable[[], T]) -> T:
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None:
                expires_at, value = hit
                if expires_at > time.monotonic() or key in self._refreshing:
                    return value  # type: ignore[return-value]
            self._refreshing.add(key)
        try:
            value = compute()
        finally:
            with self._lock:
                self._refreshing.discard(key)
        with self._lock:
            self._entries[key] = (time.monotonic() + self.ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._refreshing.clear()
