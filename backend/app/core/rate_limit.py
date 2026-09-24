"""Lightweight in-process rate limiting.

A sliding-window limiter keyed by client IP, used to slow credential
brute-forcing on login and cost abuse of the LLM-backed Specs Guard.

Scope: state is per-process, so this protects a single-instance deployment
(the current docker-compose setup). Behind a load balancer with multiple
workers, enforce limits at the gateway or back this with Redis instead.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """FastAPI dependency: allow at most ``times`` calls per ``seconds`` per IP."""

    _instances: list["RateLimiter"] = []

    def __init__(self, times: int, seconds: float) -> None:
        self.times = times
        self.seconds = seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        RateLimiter._instances.append(self)

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self.seconds:
            window.popleft()
        if len(window) >= self.times:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please wait a moment and try again.",
            )
        window.append(now)

    def reset(self) -> None:
        self._hits.clear()

    @classmethod
    def reset_all(cls) -> None:
        """Clear every limiter's state. Intended for tests."""
        for limiter in cls._instances:
            limiter.reset()
