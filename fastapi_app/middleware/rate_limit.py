from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, Request, Response, status

_buckets: dict[str, dict[str, float]] = {}
_MAX_AGE_S = 24 * 60 * 60


def _cleanup_old_buckets() -> None:
    now = time.time()
    stale = [k for k, v in _buckets.items() if now - v["last_refill"] > _MAX_AGE_S]
    for k in stale:
        del _buckets[k]


def get_rate_limit_status(api_key: str) -> dict[str, Any] | None:
    bucket = _buckets.get(api_key)
    if not bucket:
        return None
    return {
        "tokens_remaining": int(bucket["tokens"]),
        "last_refill": bucket["last_refill"],
    }


_cleanup_task: "asyncio.Task | None" = None


def start_cleanup_task() -> None:
    import asyncio
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        async def _loop() -> None:
            while True:
                await asyncio.sleep(_MAX_AGE_S)
                _cleanup_old_buckets()
        _cleanup_task = asyncio.create_task(_loop())


def stop_cleanup_interval() -> None:
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        _cleanup_task = None


async def rate_limit(request: Request, response: Response) -> dict[str, Any] | None:
    app = request.state.app if hasattr(request.state, "app") else None

    if not app:
        return None

    app_api_key = (
        app.get("api_key") if isinstance(app, dict) else getattr(app, "api_key", None)
    )
    if not app_api_key:
        return None

    max_rps = (
        app.get("max_rps") if isinstance(app, dict) else getattr(app, "max_rps", 10)
    )
    now = time.time()

    bucket = _buckets.get(app_api_key)
    if not bucket:
        bucket = {"tokens": max_rps, "last_refill": now}
        _buckets[app_api_key] = bucket

    time_delta = now - bucket["last_refill"]
    tokens_to_add = time_delta * max_rps
    bucket["tokens"] = min(max_rps, bucket["tokens"] + tokens_to_add)
    bucket["last_refill"] = now

    if bucket["tokens"] < 1:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for this API key",
            headers={
                "Retry-After": str(max(1, int((1 - bucket["tokens"]) / max_rps))),
            },
        )

    bucket["tokens"] -= 1

    response.headers["X-RateLimit-Limit"] = str(max_rps)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))
    reset_time = now + ((max_rps - bucket["tokens"]) / max_rps)
    response.headers["X-RateLimit-Reset"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(reset_time)
    )

    return {
        "limit": max_rps,
        "remaining": int(bucket["tokens"]),
    }
