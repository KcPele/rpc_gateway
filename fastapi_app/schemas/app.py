from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateAppRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    chain_name: str = Field(..., min_length=1, max_length=50)
    chain_id: str = Field(..., min_length=1, max_length=50)


class UpdateAppRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class AppResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    chain_name: str
    chain_id: str
    max_rps: int
    daily_requests_limit: int
    requests: int = 0
    daily_requests: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AppWithKeyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    api_key: str
    chain_name: str
    chain_id: str
    max_rps: int
    daily_requests_limit: int
    requests: int = 0
    daily_requests: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    total_apps: int
    has_next_page: bool
    has_prev_page: bool


class UserAppsResponse(BaseModel):
    apps: list[AppResponse]
    pagination: PaginationInfo


class DashboardStats(BaseModel):
    total_apps: int
    active_apps: int
    total_requests: int
    todays_requests: int
    max_apps: int = 5


class UsageInfo(BaseModel):
    total_requests: int
    daily_requests: int
    daily_limit: int
    usage_percentage: int
    max_rps: int
    last_reset_date: Optional[datetime] = None


class HourlyBreakdown(BaseModel):
    hour: int
    requests: int


class AppUsageAnalytics(BaseModel):
    app: dict[str, Any]
    usage: UsageInfo
    hourly_breakdown: list[HourlyBreakdown]


class AppSummary(BaseModel):
    id: str
    name: str
    chain_name: str
    total_requests: int
    daily_requests: int
    daily_limit: int
    usage_percentage: int
    is_active: bool


class AllAppsUsageSummary(BaseModel):
    total_apps: int
    active_apps: int
    total_requests: int
    daily_requests: int


class AllAppsUsageAnalytics(BaseModel):
    summary: AllAppsUsageSummary
    apps: list[AppSummary]
