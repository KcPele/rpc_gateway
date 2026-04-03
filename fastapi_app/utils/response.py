from __future__ import annotations

from datetime import datetime
from typing import Generic, Optional, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


def success_response(
    data: T | None = None,
    message: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    """Return a standardized success JSON response."""
    body: dict[str, object] = {"success": True}
    if message is not None:
        body["message"] = message
    if data is not None:
        body["data"] = _serialize(data)
    return JSONResponse(status_code=status_code, content=body)


def error_response(
    error: str | dict[str, object],
    status_code: int = 500,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    """Return a standardized error JSON response."""
    body: dict[str, object] = {"success": False, "error": error}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    """Serialize datetime to JS-compatible ISO string (milliseconds, Z suffix).

    Python's isoformat() emits microseconds (6 decimal places) which
    JavaScript's Date constructor rejects → RangeError: Invalid time value.
    """
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _serialize(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value
