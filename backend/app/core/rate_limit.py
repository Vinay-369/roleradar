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
from app.modules.auth.dependencies import get_optional_current_user


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


def _extract_client_ip(request: Request) -> str:
    """Extracts client IP safely checking forwarded headers with socket fallback."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        client_ip = xff.split(",")[0].strip()
        if client_ip:
            return client_ip
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def rate_limit(
    max_requests: int | None = None,
    window_seconds: int | None = None,
    key_prefix: str = "endpoint",
) -> Callable:
    """
    FastAPI dependency factory enforcing rate limits on authenticated or unauthenticated routes.
    - Authenticated routes: keyed by authenticated user ID.
    - Unauthenticated routes: keyed by client IP.
    """

    async def dependency(
        request: Request,
        current_user: dict | None = Depends(get_optional_current_user),
        settings: Settings = Depends(get_settings),
    ):
        if not settings.RATE_LIMITING_ENABLED:
            return

        eff_max = max_requests if max_requests is not None else settings.AUTH_RATE_LIMIT_MAX_REQUESTS
        eff_window = window_seconds if window_seconds is not None else settings.AUTH_RATE_LIMIT_WINDOW_SECONDS

        # Key by user_id if authenticated; otherwise fallback to client IP
        if current_user and "_id" in current_user:
            identifier = str(current_user["_id"])
        else:
            identifier = _extract_client_ip(request)

        rate_key = f"{key_prefix}:{identifier}"
        allowed, retry_after = _global_limiter.is_allowed(rate_key, eff_max, eff_window)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {eff_max} requests per {eff_window}s allowed.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def auth_rate_limit(key_prefix: str = "auth") -> Callable:
    """Convenience dependency factory for unauthenticated auth endpoints using settings."""
    return rate_limit(max_requests=None, window_seconds=None, key_prefix=key_prefix)

