from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth schemas ──────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UpdateEmailRequest(BaseModel):
    email: EmailStr
    new_email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    isAdmin: bool = False
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class AuthDataResponse(BaseModel):
    success: bool = True
    data: dict

    @classmethod
    def create(cls, token: str, user) -> AuthDataResponse:
        return cls(
            success=True,
            data={
                "token": token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "isAdmin": user.is_admin,
                    "isActive": user.is_active,
                    "createdAt": user.created_at,
                    "updatedAt": user.updated_at,
                },
            },
        )


class ExportAppResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    chainName: str
    chainId: str
    isActive: bool
    requests: int
    dailyRequests: int
    maxRps: int
    dailyRequestsLimit: int
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class ExportDataResponse(BaseModel):
    user: UserResponse
    apps: list[ExportAppResponse]
    exportDate: datetime


# ── App schemas ───────────────────────────────────────────────────────────────


class CreateAppRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    chain_name: str = Field(..., min_length=1, max_length=50)
    chain_id: str = Field(..., min_length=1, max_length=50)


class UpdateAppRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class AppResponse(BaseModel):
    _id: str
    userId: str
    name: str
    description: Optional[str] = None
    apiKey: Optional[str] = None
    chainName: str
    chainId: str
    isActive: bool = True
    requests: int = 0
    dailyRequests: int = 0
    maxRps: int
    dailyRequestsLimit: int
    lastResetDate: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class AppWithKeyResponse(AppResponse):
    pass


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


# ── Admin schemas ─────────────────────────────────────────────────────────────


class AddChainRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    chain_id: str = Field(..., min_length=1, max_length=50)
    is_enabled: bool = True
    admin_notes: Optional[str] = None


class UpdateChainRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    new_chain_id: Optional[str] = Field(None, min_length=1, max_length=50)
    is_enabled: Optional[bool] = None
    admin_notes: Optional[str] = None


class ChainResponse(BaseModel):
    _id: str
    name: str
    chainId: int
    isEnabled: bool
    adminNotes: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class AdminUpdateAppRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    user_id: Optional[str] = None
    chain_name: Optional[str] = Field(None, min_length=1, max_length=50)
    chain_id: Optional[str] = Field(None, min_length=1, max_length=50)
    max_rps: Optional[int] = Field(None, ge=0)
    daily_requests_limit: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    api_key: Optional[str] = None
    requests: Optional[int] = Field(None, ge=0)
    daily_requests: Optional[int] = Field(None, ge=0)
    last_reset_date: Optional[datetime] = None


class AdminUpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = None


class DefaultAppSettingsResponse(BaseModel):
    _id: str
    maxRps: int
    dailyRequestsLimit: int
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class UpdateDefaultAppSettingsRequest(BaseModel):
    max_rps: Optional[int] = Field(None, gt=0)
    daily_requests_limit: Optional[int] = Field(None, gt=0)


class PaginatedUsersResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    limit: int
    totalPages: int


class PaginatedAppsResponse(BaseModel):
    apps: list[AppResponse]
    total: int
    page: int
    limit: int
    totalPages: int


class NodeHealthCheck(BaseModel):
    url: Optional[str] = None
    status: str
    syncing: Any = None
    head_slot: Any = None
    error: Optional[str] = None


class NodeHealthService(BaseModel):
    status: str
    total_nodes: int
    available_nodes: int
    nodes: list[NodeHealthCheck]


class NodeHealthResponse(BaseModel):
    chain: str
    timestamp: datetime
    execution: NodeHealthService
    consensus: NodeHealthService
    metrics: NodeHealthService
    overall: str


class NodeMetricsData(BaseModel):
    go_runtime: Optional[dict[str, Any]] = None
    sync: Optional[dict[str, Any]] = None


class NodeMetricsNode(BaseModel):
    node_index: int
    node_url: str
    status: str
    metrics: Optional[NodeMetricsData] = None
    error: Optional[str] = None


class NodeMetricsSummary(BaseModel):
    chain: str
    timestamp: datetime
    total_nodes: int
    available_nodes: int
    nodes: list[NodeMetricsNode]


# ── Proxy schemas ─────────────────────────────────────────────────────────────


class ProxyHealthCheck(BaseModel):
    url: Optional[str] = None
    status: str


class ProxyHealthResponse(BaseModel):
    status: str
    chain: str
    checks: dict[str, ProxyHealthCheck]
    timestamp: datetime


# ── Generic response wrapper ──────────────────────────────────────────────────


class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
