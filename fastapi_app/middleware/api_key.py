from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import HTTPException, Request, status

from fastapi_app.database import App

# ── In-memory cache ────────────────────────────────────────────────────────────
# Stores only the fields we actually need, not a full model_dump.
_cached_apps: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL_S = 60

# ── Pending DB writes ──────────────────────────────────────────────────────────
# Accumulate increments and flush to Mongo periodically instead of on every hit.
_pending_updates: dict[str, dict[str, Any]] = {}
_flush_task: asyncio.Task | None = None
FLUSH_INTERVAL_S = 5


def _extract_app_fields(app: App) -> dict[str, Any]:
    """Store only what validate_api_key and rate_limit actually need."""
    return {
        "id": str(app.id),
        "api_key": app.api_key,
        "chain_name": app.chain_name,
        "user_id": str(app.user_id),
        "max_rps": app.max_rps,
        "daily_requests_limit": app.daily_requests_limit,
        "daily_requests": app.daily_requests,
        "last_reset_date": app.last_reset_date,
        "is_active": app.is_active,
    }


async def _flush_pending_updates() -> None:
    """Periodically write accumulated request counters to MongoDB."""
    while True:
        await asyncio.sleep(FLUSH_INTERVAL_S)
        if not _pending_updates:
            continue

        snapshot = dict(_pending_updates)
        _pending_updates.clear()

        for api_key, delta in snapshot.items():
            try:
                app = await App.find_one(App.api_key == api_key)
                if not app:
                    continue

                inc: dict[str, Any] = {}
                if delta.get("requests"):
                    inc["requests"] = delta["requests"]
                if delta.get("daily_requests"):
                    inc["daily_requests"] = delta["daily_requests"]

                update: dict[str, Any] = {}
                if inc:
                    update["$inc"] = inc
                if "last_reset_date" in delta:
                    from datetime import datetime, timezone
                    update.setdefault("$set", {})["last_reset_date"] = datetime.now(timezone.utc)
                    update["$set"]["daily_requests"] = 1

                if update:
                    await app.get_motor_collection().update_one(
                        {"_id": app.id}, update
                    )
                    # Invalidate cache so next read gets fresh counts
                    _cached_apps.pop(api_key, None)
            except Exception:
                pass


def start_flush_task() -> None:
    global _flush_task
    if _flush_task is None or _flush_task.done():
        _flush_task = asyncio.create_task(_flush_pending_updates())


def stop_flush_task() -> None:
    global _flush_task
    if _flush_task and not _flush_task.done():
        _flush_task.cancel()
        _flush_task = None


def invalidate_api_key_cache(api_key: str) -> None:
    _cached_apps.pop(api_key, None)


def clear_api_key_cache() -> None:
    _cached_apps.clear()


async def validate_api_key(request: Request) -> dict[str, Any]:
    key = request.path_params.get("key")
    requested_chain = request.path_params.get("chain", "").lower()

    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing API key in URL path")
    if not requested_chain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing chain in URL path")

    now = time.time()

    cached = _cached_apps.get(key)
    if cached and now - cached[1] < CACHE_TTL_S:
        app_doc = cached[0]
    else:
        _cached_apps.pop(key, None)
        app = await App.find_one(App.api_key == key, App.is_active == True)
        if not app:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or inactive API key")
        app_doc = _extract_app_fields(app)
        _cached_apps[key] = (app_doc, now)

    if app_doc["chain_name"].lower() != requested_chain:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is not valid for chain '{requested_chain}'",
        )

    today = time.strftime("%Y-%m-%d")
    last_reset = app_doc.get("last_reset_date")
    last_reset_date: str | None = None
    if last_reset:
        try:
            last_reset_date = time.strftime("%Y-%m-%d", time.gmtime(last_reset.timestamp()))
        except Exception:
            pass

    needs_reset = last_reset_date != today

    pending = _pending_updates.setdefault(key, {"requests": 0, "daily_requests": 0})

    if needs_reset:
        pending["last_reset_date"] = True
        pending["requests"] = pending.get("requests", 0) + 1
        effective_daily = 1
    else:
        pending["requests"] = pending.get("requests", 0) + 1
        pending["daily_requests"] = pending.get("daily_requests", 0) + 1
        effective_daily = int(app_doc.get("daily_requests") or 0) + pending["daily_requests"]

    if effective_daily > int(app_doc.get("daily_requests_limit") or 0):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily request limit exceeded for this app")

    return app_doc
