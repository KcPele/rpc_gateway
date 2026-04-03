from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


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
    users: list["UserResponse"]
    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedAppsResponse(BaseModel):
    apps: list["AppResponse"]
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


from fastapi_app.schemas.app import AppResponse
from fastapi_app.schemas.auth import UserResponse

PaginatedUsersResponse.model_rebuild()
PaginatedAppsResponse.model_rebuild()
