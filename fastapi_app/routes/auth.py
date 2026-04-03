from __future__ import annotations

import os
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status

from fastapi_app.database import App, User
from fastapi_app.config.settings import settings as app_settings
from fastapi_app.middleware.auth import get_current_user
from fastapi_app.schemas import (
    AuthDataResponse,
    ExportDataResponse,
    LoginRequest,
    RegisterRequest,
    UpdateEmailRequest,
    UpdatePasswordRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "isAdmin": user.is_admin,
        "isActive": user.is_active,
        "createdAt": user.created_at,
        "updatedAt": user.updated_at,
    }


def _create_token(user_id: str) -> str:
    secret = app_settings.jwt_secret
    return jwt.encode(
        {"id": user_id, "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7},
        secret,
        algorithm="HS256",
    )


@router.post("/register", response_model=AuthDataResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest):
    existing = await User.find_one(User.email == payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        email=payload.email,
        password=User.hash_password(payload.password),
        name=payload.name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await user.insert()

    token = _create_token(str(user.id))
    return {"success": True, "data": {"token": token, "user": _user_response(user)}}


@router.post("/login", response_model=AuthDataResponse)
async def login_user(payload: LoginRequest):
    user = await User.find_one(User.email == payload.email)
    if not user or not user.verify_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = _create_token(str(user.id))
    return {"success": True, "data": {"token": token, "user": _user_response(user)}}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"success": True, "data": _user_response(user)}


@router.get("/account")
async def get_account(user: User = Depends(get_current_user)):
    return {"success": True, "data": _user_response(user)}


@router.patch("/password")
async def update_password(payload: UpdatePasswordRequest, user: User = Depends(get_current_user)):
    if not user.verify_password(payload.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.password = User.hash_password(payload.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await user.save()

    return {"success": True, "message": "Password updated successfully"}


@router.patch("/email")
async def update_email(payload: UpdateEmailRequest, user: User = Depends(get_current_user)):
    if not user.verify_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect",
        )

    existing = await User.find_one(User.email == payload.new_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already in use by another account",
        )

    user.email = payload.new_email
    user.updated_at = datetime.now(timezone.utc)
    await user.save()

    return {"success": True, "message": "Email updated successfully"}


@router.get("/export")
async def export_user_data(user: User = Depends(get_current_user)):
    apps = await App.find(App.user_id == str(user.id)).to_list()

    apps_data = [
        {
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "chain_name": a.chain_name,
            "is_active": a.is_active,
            "requests": a.requests,
            "daily_requests": a.daily_requests,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }
        for a in apps
    ]

    return {
        "success": True,
        "data": {
            "user": _user_response(user),
            "apps": apps_data,
            "export_date": datetime.now(timezone.utc),
        },
    }
