from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UpdateEmailRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuthDataResponse(BaseModel):
    token: str
    user: UserResponse


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
