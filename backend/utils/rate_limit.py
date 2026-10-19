"""A small in-memory, per-client rate limiter.

Limits are tracked per worker process. That is sufficient to slow down brute
force attempts and accidental floods in a single-instance deployment; a shared
store (e.g. Redis) would be needed for strict limits across many workers.
"""

import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request

_MAX_TRACKED_KEYS = 10000


class RateLimiter:
    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key, limit, window_seconds):
        """Record a request. Returns ``(allowed, retry_after_seconds)``."""
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._purge(now, window_seconds)
            hits = self._hits[key]
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False, max(1, int(window_seconds - (now - hits[0])) + 1)
            hits.append(now)
            return True, 0

    def _purge(self, now, window_seconds):
        for key in list(self._hits):
            hits = self._hits[key]
            if not hits or now - hits[-1] >= window_seconds:
                del self._hits[key]

    def reset(self):
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def rate_limit(bucket, config_key, window_seconds=60):
    """Limit a view to ``app.config[config_key]`` requests per window per client IP."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            limit = current_app.config.get(config_key, 0)
            if current_app.config.get("RATE_LIMIT_ENABLED", True) and limit:
                key = f"{bucket}:{request.remote_addr}"
                allowed, retry_after = limiter.hit(key, limit, window_seconds)
                if not allowed:
                    response = jsonify(
                        {"error": "Too many requests. Please wait a moment and try again."}
                    )
                    response.status_code = 429
                    response.headers["Retry-After"] = str(retry_after)
                    return response
            return f(*args, **kwargs)

        return wrapped

    return decorator
