from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from fastapi_app.middleware.admin import require_admin
from fastapi_app.middleware.auth import get_current_user
from fastapi_app.services import admin_management as admin_mgmt_service

router = APIRouter(tags=["admin-management"])


@router.patch("/apps/{app_id}")
async def update_app_details(app_id: str, payload: dict, user=Depends(require_admin)):
    return await admin_mgmt_service.update_app_details(app_id, payload)


@router.patch("/users/{user_id}")
async def update_user_details(user_id: str, payload: dict, user=Depends(require_admin)):
    return await admin_mgmt_service.update_user_details(user_id, payload)


@router.get("/users")
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    user=Depends(require_admin),
):
    return await admin_mgmt_service.get_all_users(page, limit)


@router.get("/apps")
async def get_all_apps(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    user_id: str | None = Query(None),
    user=Depends(require_admin),
):
    return await admin_mgmt_service.get_all_apps(page, limit, user_id)


@router.get("/default-app-settings")
async def get_default_app_settings(user=Depends(require_admin)):
    return await admin_mgmt_service.get_default_app_settings()


@router.patch("/default-app-settings")
async def update_default_app_settings(
    payload: dict,
    user=Depends(require_admin),
):
    return await admin_mgmt_service.update_default_app_settings(payload)
