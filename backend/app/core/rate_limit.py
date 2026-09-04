"""
In-memory sliding window rate limiter for expensive API endpoints.
Protects generative, parsing, and LLM endpoints against request flooding.
"""
import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.modules.auth.dependencies import get_current_user


class InMemorySlidingWindowLimiter:
    """
    Thread-safe sliding window rate limiter.
    Records request timestamps per key and prunes timestamps older than the window.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._requests[key]
            # Prune timestamps outside window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._requests[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, retry_after

            self._requests[key].append(now)
            return True, 0

    def reset(self):
        """Clears all rate limit state (useful for tests)."""
        with self._lock:
            self._requests.clear()


_global_limiter = InMemorySlidingWindowLimiter()


def get_global_limiter() -> InMemorySlidingWindowLimiter:
    return _global_limiter


def rate_limit(
    max_requests: int,
    window_seconds: int = 60,
    key_prefix: str = "endpoint",
) -> Callable:
    """
    FastAPI dependency factory enforcing rate limits on authenticated or unauthenticated routes.
    """

    async def dependency(
        request: Request,
        current_user: dict | None = Depends(get_current_user),
        settings: Settings = Depends(get_settings),
    ):
        if not settings.RATE_LIMITING_ENABLED:
            return

        # Key by user_id if authenticated; otherwise fallback to client IP
        if current_user and "_id" in current_user:
            identifier = str(current_user["_id"])
        else:
            identifier = request.client.host if request.client else "anonymous"

        rate_key = f"{key_prefix}:{identifier}"
        allowed, retry_after = _global_limiter.is_allowed(rate_key, max_requests, window_seconds)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s allowed.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
