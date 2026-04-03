from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AddChainRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=100)
    chain_id: str = Field(..., min_length=1, max_length=50, alias="chainId")
    is_enabled: bool = Field(True, alias="isEnabled")
    admin_notes: Optional[str] = Field(None, alias="adminNotes")


class UpdateChainRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    new_chain_id: Optional[str] = Field(
        None, min_length=1, max_length=50, alias="newChainId"
    )
    is_enabled: Optional[bool] = Field(None, alias="isEnabled")
    admin_notes: Optional[str] = Field(None, alias="adminNotes")


class ChainResponse(BaseModel):
    _id: str
    name: str
    chainId: int
    isEnabled: bool
    adminNotes: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class AdminUpdateAppRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    user_id: Optional[str] = Field(None, alias="userId")
    chain_name: Optional[str] = Field(
        None, min_length=1, max_length=50, alias="chainName"
    )
    chain_id: Optional[str] = Field(None, min_length=1, max_length=50, alias="chainId")
    max_rps: Optional[int] = Field(None, ge=0, alias="maxRps")
    daily_requests_limit: Optional[int] = Field(None, ge=0, alias="dailyRequestsLimit")
    is_active: Optional[bool] = Field(None, alias="isActive")
    api_key: Optional[str] = Field(None, alias="apiKey")
    requests: Optional[int] = Field(None, ge=0)
    daily_requests: Optional[int] = Field(None, ge=0, alias="dailyRequests")
    last_reset_date: Optional[datetime] = Field(None, alias="lastResetDate")


class AdminUpdateUserRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = Field(None, alias="isActive")


class DefaultAppSettingsResponse(BaseModel):
    _id: str
    maxRps: int
    dailyRequestsLimit: int
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class UpdateDefaultAppSettingsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    max_rps: Optional[int] = Field(None, gt=0, alias="maxRps")
    daily_requests_limit: Optional[int] = Field(None, gt=0, alias="dailyRequestsLimit")


class PaginatedUsersResponse(BaseModel):
    users: list["UserResponse"]
    total: int
    page: int
    limit: int
    totalPages: int


class PaginatedAppsResponse(BaseModel):
    apps: list["AppResponse"]
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


from fastapi_app.schemas.app import AppResponse
from fastapi_app.schemas.auth import UserResponse

PaginatedUsersResponse.model_rebuild()
PaginatedAppsResponse.model_rebuild()
