from __future__ import annotations

import os
from datetime import datetime, timezone
from math import ceil
from uuid import uuid4

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from fastapi_app.database import App, Chain, DefaultAppSettings, User
from fastapi_app.middleware.auth import get_current_user
from fastapi_app.schemas.app import CreateAppRequest, UpdateAppRequest

router = APIRouter(prefix="/apps", tags=["apps"])

MAX_APPS_PER_USER = 5


def _app_dict(app: App) -> dict:
    return {
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
        "createdAt": app.created_at,
        "updatedAt": app.updated_at,
    }


def _app_with_key_dict(app: App) -> dict:
    return {
        "_id": str(app.id),
        "name": app.name,
        "description": app.description,
        "userId": app.user_id,
        "apiKey": app.api_key,
        "chainName": app.chain_name,
        "chainId": app.chain_id,
        "maxRps": app.max_rps,
        "dailyRequestsLimit": app.daily_requests_limit,
        "requests": app.requests,
        "dailyRequests": app.daily_requests,
        "isActive": app.is_active,
        "createdAt": app.created_at,
        "updatedAt": app.updated_at,
    }


async def _get_default_limits() -> tuple[int, int]:
    default_settings = await DefaultAppSettings.find_one()
    if default_settings:
        return default_settings.max_rps, default_settings.daily_requests_limit
    app_max_rps = int(os.getenv("DEFAULT_MAX_RPS", "200"))
    app_daily_limit = int(os.getenv("DEFAULT_DAILY_REQUESTS", "1000000"))
    return app_max_rps, app_daily_limit


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_app(
    payload: CreateAppRequest,
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    app_count = await App.find(App.user_id == user_id).count()
    if app_count >= MAX_APPS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User cannot create more than {MAX_APPS_PER_USER} apps.",
        )

    chain = await Chain.find_one(
        Chain.name == payload.chain_name,
        Chain.chain_id == payload.chain_id,
        Chain.is_enabled == True,
    )
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain '{payload.chain_name}' with chainId '{payload.chain_id}' not found or is not enabled.",
        )

    max_rps, daily_limit = await _get_default_limits()

    new_app = App(
        name=payload.name,
        description=payload.description,
        user_id=user_id,
        chain_name=chain.name,
        chain_id=chain.chain_id,
        api_key=str(uuid4()),
        max_rps=max_rps,
        daily_requests_limit=daily_limit,
    )
    await new_app.insert()

    return {
        "success": True,
        "message": "App created successfully.",
        "data": _app_dict(new_app),
    }


@router.get("")
async def get_user_apps(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)
    skip = (page - 1) * limit

    query = App.find(App.user_id == user_id)
    apps, total_apps = (
        await query.sort("-created_at").skip(skip).limit(limit).to_list(),
        await query.count(),
    )

    total_pages = ceil(total_apps / limit) if total_apps > 0 else 0

    return {
        "success": True,
        "message": "User applications retrieved successfully.",
        "data": {
            "apps": [_app_dict(a) for a in apps],
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalApps": total_apps,
                "hasNextPage": page < total_pages,
                "hasPrevPage": page > 1,
            },
        },
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    total_apps = await App.find(App.user_id == user_id).count()
    active_apps = await App.find(App.user_id == user_id, App.is_active == True).count()

    all_apps = await App.find(App.user_id == user_id).to_list()
    total_requests = sum(a.requests for a in all_apps)
    todays_requests = sum(a.daily_requests for a in all_apps)

    return {
        "success": True,
        "message": "Dashboard statistics retrieved successfully.",
        "data": {
            "stats": {
                "totalApps": total_apps,
                "activeApps": active_apps,
                "totalRequests": total_requests,
                "todaysRequests": todays_requests,
                "maxApps": MAX_APPS_PER_USER,
            },
        },
    }


@router.get("/usage/all")
async def get_all_apps_usage(
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    apps = await App.find(App.user_id == user_id).to_list()

    total_requests = sum(a.requests for a in apps)
    daily_requests = sum(a.daily_requests for a in apps)
    active_apps = sum(1 for a in apps if a.is_active)

    apps_summary = []
    for app in apps:
        usage_pct = (
            round((app.daily_requests / app.daily_requests_limit) * 100)
            if app.daily_requests_limit > 0
            else 0
        )
        apps_summary.append(
            {
                "id": str(app.id),
                "name": app.name,
                "chainName": app.chain_name,
                "totalRequests": app.requests,
                "dailyRequests": app.daily_requests,
                "dailyLimit": app.daily_requests_limit,
                "usagePercentage": usage_pct,
                "isActive": app.is_active,
            }
        )

    apps_summary.sort(key=lambda a: a["dailyRequests"], reverse=True)

    return {
        "success": True,
        "message": "Usage analytics retrieved successfully.",
        "data": {
            "analytics": {
                "summary": {
                    "totalApps": len(apps),
                    "activeApps": active_apps,
                    "totalRequests": total_requests,
                    "dailyRequests": daily_requests,
                },
                "apps": apps_summary,
            },
        },
    }


@router.get("/{app_id}")
async def get_user_app(
    app_id: str,
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    app = await App.find_one(App.id == PydanticObjectId(app_id), App.user_id == user_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found or access denied.",
        )

    return {
        "success": True,
        "message": "App retrieved successfully.",
        "data": _app_with_key_dict(app),
    }


@router.patch("/{app_id}")
async def update_user_app(
    app_id: str,
    payload: UpdateAppRequest,
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    app = await App.find_one(App.id == PydanticObjectId(app_id), App.user_id == user_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found or access denied.",
        )

    if payload.name is not None:
        app.name = payload.name
    if payload.description is not None:
        app.description = payload.description

    await app.save()

    return {
        "success": True,
        "message": "App updated successfully.",
        "data": _app_dict(app),
    }


@router.delete("/{app_id}", status_code=status.HTTP_200_OK)
async def delete_user_app(
    app_id: str,
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    app = await App.find_one(App.id == PydanticObjectId(app_id), App.user_id == user_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found or access denied.",
        )

    await app.delete()

    return {
        "success": True,
        "message": "App deleted successfully.",
    }


@router.post("/{app_id}/regenerate-key")
async def regenerate_api_key(
    app_id: str,
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    app = await App.find_one(App.id == PydanticObjectId(app_id), App.user_id == user_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found or access denied.",
        )

    app.api_key = str(uuid4())
    await app.save()

    return {
        "success": True,
        "message": "API key regenerated successfully.",
        "data": app.api_key,
    }


@router.get("/{app_id}/usage")
async def get_app_usage_analytics(
    app_id: str,
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    app = await App.find_one(App.id == PydanticObjectId(app_id), App.user_id == user_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found.",
        )

    usage_pct = (
        round((app.daily_requests / app.daily_requests_limit) * 100)
        if app.daily_requests_limit > 0
        else 0
    )

    hourly_data = []
    avg_per_hour = app.daily_requests / 24 if app.daily_requests > 0 else 0
    for i in range(24):
        hourly_data.append(
            {
                "hour": i,
                "requests": int(avg_per_hour),
            }
        )

    return {
        "success": True,
        "message": "App usage analytics retrieved successfully.",
        "data": {
            "analytics": {
                "app": {
                    "id": str(app.id),
                    "name": app.name,
                    "chainName": app.chain_name,
                },
                "usage": {
                    "totalRequests": app.requests,
                    "dailyRequests": app.daily_requests,
                    "dailyLimit": app.daily_requests_limit,
                    "usagePercentage": usage_pct,
                    "maxRps": app.max_rps,
                    "lastResetDate": app.last_reset_date,
                },
                "hourlyBreakdown": hourly_data,
            },
        },
    }
