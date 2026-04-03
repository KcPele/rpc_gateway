from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str


class UpdatePasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., min_length=6, alias="newPassword")


class UpdateEmailRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
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
    def create(cls, token: str, user) -> "AuthDataResponse":
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
