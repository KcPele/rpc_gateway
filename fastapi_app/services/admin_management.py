from __future__ import annotations

from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import HTTPException, Query, status

from fastapi_app.database import App, Chain, DefaultAppSettings, User
from fastapi_app.middleware.admin import require_admin
from fastapi_app.middleware.auth import get_current_user


async def update_app_details(app_id: str, payload: dict) -> dict:
    """Update app details as admin."""
    allowed_fields = [
        "name",
        "description",
        "user_id",
        "userId",
        "chain_name",
        "chainName",
        "chain_id",
        "chainId",
        "max_rps",
        "maxRps",
        "daily_requests_limit",
        "dailyRequestsLimit",
        "is_active",
        "isActive",
        "api_key",
        "apiKey",
        "requests",
        "daily_requests",
        "dailyRequests",
        "last_reset_date",
        "lastResetDate",
    ]

    filtered = {}
    for key, value in payload.items():
        snake = (
            key.replace("Id", "_id")
            .replace("Name", "_name")
            .replace("Rps", "_rps")
            .replace("Limit", "_limit")
            .replace("Requests", "_requests")
            .replace("Date", "_date")
            .replace("Key", "_key")
            .replace("Active", "_active")
        )
        if snake in allowed_fields and value is not None:
            if snake == "api_key" and value == "":
                continue
            filtered[snake] = value

    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update.",
        )

    app = await App.get(app_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App with ID '{app_id}' not found.",
        )

    for key, value in filtered.items():
        if hasattr(app, key):
            setattr(app, key, value)

    app.updated_at = datetime.now(timezone.utc)
    await app.save()

    return {
        "success": True,
        "message": "App details updated successfully.",
        "data": {
            "_id": str(app.id),
            "name": app.name,
            "description": app.description,
            "userId": app.user_id,
            "chainName": app.chain_name,
            "chainId": app.chain_id,
            "maxRps": app.max_rps,
            "dailyRequestsLimit": app.daily_requests_limit,
            "requests": app.requests,
            "dailyRequests": app.daily_requests,
            "isActive": app.is_active,
            "apiKey": app.api_key,
            "createdAt": app.created_at,
            "updatedAt": app.updated_at,
        },
    }


async def update_user_details(user_id: str, payload: dict) -> dict:
    """Update user details as admin."""
    allowed_fields = ["email", "password", "is_active", "isActive"]
    filtered = {}
    for key, value in payload.items():
        snake = key.replace("Active", "_active")
        if snake in allowed_fields and value is not None:
            if snake == "password" and value == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password cannot be an empty string.",
                )
            filtered[snake] = value

    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update.",
        )

    target_user = await User.get(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    if "password" in filtered:
        if "email" in filtered:
            target_user.email = filtered.pop("email")
        if "is_active" in filtered:
            target_user.is_active = filtered.pop("is_active")
        target_user.password = User.hash_password(filtered.pop("password"))
        target_user.updated_at = datetime.now(timezone.utc)
        await target_user.save()
    else:
        for key, value in filtered.items():
            if hasattr(target_user, key):
                setattr(target_user, key, value)
        target_user.updated_at = datetime.now(timezone.utc)
        await target_user.save()

    user_obj = {
        "_id": str(target_user.id),
        "email": target_user.email,
        "isAdmin": target_user.is_admin,
        "isActive": target_user.is_active,
        "createdAt": target_user.created_at,
        "updatedAt": target_user.updated_at,
    }

    return {
        "success": True,
        "message": "User details updated successfully.",
        "data": user_obj,
    }


async def get_all_users(page: int = 1, limit: int = 10) -> dict:
    """Get paginated list of all users."""
    skip = (page - 1) * limit
    users = await User.find().sort("-created_at").skip(skip).limit(limit).to_list()
    total = await User.count()

    return {
        "success": True,
        "data": {
            "users": [
                {
                    "_id": str(u.id),
                    "email": u.email,
                    "isAdmin": u.is_admin,
                    "isActive": u.is_active,
                    "createdAt": u.created_at,
                    "updatedAt": u.updated_at,
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit,
        },
    }


async def get_all_apps(
    page: int = 1, limit: int = 10, user_id: str | None = None
) -> dict:
    """Get paginated list of all apps."""
    skip = (page - 1) * limit
    query = App.find()
    if user_id:
        query = App.find(App.user_id == user_id)

    apps = await query.sort("-created_at").skip(skip).limit(limit).to_list()
    total = await query.count()

    return {
        "success": True,
        "data": {
            "apps": [
                {
                    "_id": str(a.id),
                    "name": a.name,
                    "description": a.description,
                    "userId": a.user_id,
                    "chainName": a.chain_name,
                    "chainId": a.chain_id,
                    "maxRps": a.max_rps,
                    "dailyRequestsLimit": a.daily_requests_limit,
                    "requests": a.requests,
                    "dailyRequests": a.daily_requests,
                    "isActive": a.is_active,
                    "createdAt": a.created_at,
                    "updatedAt": a.updated_at,
                }
                for a in apps
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit,
        },
    }


async def get_default_app_settings() -> dict:
    """Get default app settings."""
    from fastapi_app.config.settings import settings

    settings_doc = await DefaultAppSettings.find_one()

    if not settings_doc:
        settings_doc = DefaultAppSettings(
            max_rps=settings.default_max_rps,
            daily_requests_limit=settings.default_daily_requests,
        )
        await settings_doc.insert()

    return {
        "success": True,
        "data": {
            "_id": str(settings_doc.id),
            "maxRps": settings_doc.max_rps,
            "dailyRequestsLimit": settings_doc.daily_requests_limit,
            "createdAt": settings_doc.created_at,
            "updatedAt": settings_doc.updated_at,
        },
    }


async def update_default_app_settings(payload: dict) -> dict:
    """Update default app settings."""
    max_rps = payload.get("maxRps", payload.get("max_rps"))
    daily_limit = payload.get("dailyRequestsLimit", payload.get("daily_requests_limit"))

    if max_rps is None and daily_limit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (maxRps or dailyRequestsLimit) must be provided.",
        )

    update_data = {}
    if max_rps is not None:
        update_data["max_rps"] = max_rps
    if daily_limit is not None:
        update_data["daily_requests_limit"] = daily_limit

    settings_doc = await DefaultAppSettings.find_one()
    if settings_doc:
        for key, value in update_data.items():
            setattr(settings_doc, key, value)
        await settings_doc.save()
    else:
        settings_doc = DefaultAppSettings(**update_data)
        await settings_doc.insert()

    return {
        "success": True,
        "data": {
            "_id": str(settings_doc.id),
            "maxRps": settings_doc.max_rps,
            "dailyRequestsLimit": settings_doc.daily_requests_limit,
            "createdAt": settings_doc.created_at,
            "updatedAt": settings_doc.updated_at,
        },
    }
