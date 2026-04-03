from __future__ import annotations

from typing import Generic, TypeVar

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


def _serialize(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value
