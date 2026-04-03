from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProxyHealthCheck(BaseModel):
    url: Optional[str] = None
    status: str


class ProxyHealthResponse(BaseModel):
    status: str
    chain: str
    checks: dict[str, ProxyHealthCheck]
    timestamp: datetime
