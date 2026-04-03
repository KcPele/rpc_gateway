from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateAppRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    chain_name: str = Field(..., min_length=1, max_length=50, alias="chainName")
    chain_id: str = Field(..., min_length=1, max_length=50, alias="chainId")


class UpdateAppRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class AppResponse(BaseModel):
    _id: str
    name: str
    description: Optional[str] = None
    userId: str
    chainName: str
    chainId: str
    maxRps: int
    dailyRequestsLimit: int
    requests: int = 0
    dailyRequests: int = 0
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class AppWithKeyResponse(AppResponse):
    apiKey: str


class PaginationInfo(BaseModel):
    currentPage: int
    totalPages: int
    totalApps: int
    hasNextPage: bool
    hasPrevPage: bool


class UserAppsResponse(BaseModel):
    apps: list[AppResponse]
    pagination: PaginationInfo


class DashboardStats(BaseModel):
    totalApps: int
    activeApps: int
    totalRequests: int
    todaysRequests: int
    maxApps: int = 5


class UsageInfo(BaseModel):
    totalRequests: int
    dailyRequests: int
    dailyLimit: int
    usagePercentage: int
    maxRps: int
    lastResetDate: Optional[datetime] = None


class HourlyBreakdown(BaseModel):
    hour: int
    requests: int


class AppUsageAnalytics(BaseModel):
    app: dict[str, Any]
    usage: UsageInfo
    hourlyBreakdown: list[HourlyBreakdown]


class AppSummary(BaseModel):
    id: str
    name: str
    chainName: str
    totalRequests: int
    dailyRequests: int
    dailyLimit: int
    usagePercentage: int
    isActive: bool


class AllAppsUsageSummary(BaseModel):
    totalApps: int
    activeApps: int
    totalRequests: int
    dailyRequests: int


class AllAppsUsageAnalytics(BaseModel):
    summary: AllAppsUsageSummary
    apps: list[AppSummary]
