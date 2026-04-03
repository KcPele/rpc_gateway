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
    chain_name: str
    chain_id: str
    is_active: bool
    requests: int
    daily_requests: int
    max_rps: int
    daily_requests_limit: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExportDataResponse(BaseModel):
    user: UserResponse
    apps: list[ExportAppResponse]
    export_date: datetime


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
    id: str
    name: str
    chain_id: str
    is_enabled: bool
    admin_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    id: str
    max_rps: int
    daily_requests_limit: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UpdateDefaultAppSettingsRequest(BaseModel):
    max_rps: Optional[int] = Field(None, gt=0)
    daily_requests_limit: Optional[int] = Field(None, gt=0)


class PaginatedUsersResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedAppsResponse(BaseModel):
    apps: list[AppResponse]
    total: int
    page: int
    limit: int
    total_pages: int


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
