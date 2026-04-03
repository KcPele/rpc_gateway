from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, Request, status

from fastapi_app.database import App

_cached_apps: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL_S = 60

_pending_updates: dict[str, dict[str, Any]] = {}


def invalidate_api_key_cache(api_key: str) -> None:
    _cached_apps.pop(api_key, None)


def clear_api_key_cache() -> None:
    _cached_apps.clear()


async def validate_api_key(request: Request) -> dict[str, Any]:
    key = request.path_params.get("key")
    requested_chain = request.path_params.get("chain", "").lower()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing API key in URL path",
        )
    if not requested_chain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing chain in URL path",
        )

    now = time.time()

    cached = _cached_apps.get(key)
    if cached and now - cached[1] < CACHE_TTL_S:
        app_doc = cached[0]
    else:
        _cached_apps.pop(key, None)
        app = await App.find_one(App.api_key == key, App.is_active == True)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or inactive API key",
            )
        app_doc = app.model_dump(by_alias=True)
        app_doc["id"] = str(app.id)
        _cached_apps[key] = (app_doc, now)

    if (app_doc.get("chain_name", "")).lower() != requested_chain:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is not valid for chain '{requested_chain}'",
        )

    today = time.strftime("%Y-%m-%d")
    last_reset = app_doc.get("last_reset_date")
    if last_reset:
        try:
            last_reset_date = time.strftime(
                "%Y-%m-%d", time.gmtime(last_reset.timestamp())
            )
        except Exception:
            last_reset_date = None
    else:
        last_reset_date = None

    needs_reset = last_reset_date != today

    pending = _pending_updates.get(key)
    if not pending:
        pending = {"requests": 0, "daily_requests": 0}
        _pending_updates[key] = pending

    if needs_reset:
        pending["daily_requests"] = 1 - int(app_doc.get("daily_requests") or 0)
        pending["last_reset_date"] = int(time.time())
        pending["requests"] += 1
    else:
        pending["requests"] += 1
        pending["daily_requests"] += 1

    effective_daily = (
        1
        if needs_reset
        else int(app_doc.get("daily_requests") or 0) + pending["daily_requests"]
    )

    if effective_daily > int(app_doc.get("daily_requests_limit") or 0):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily request limit exceeded for this app",
        )

    return app_doc
