from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi_app.middleware.admin import require_admin
from fastapi_app.middleware.auth import get_current_user
from fastapi_app.services import admin as admin_service

router = APIRouter(tags=["admin-nodes"])


@router.get("/node-health/{chain}")
async def get_node_health(
    chain: str,
    user=Depends(require_admin),
):
    return await admin_service.get_node_health(chain)


@router.get("/node-metrics/{chain}")
async def get_node_metrics(
    chain: str,
    user=Depends(require_admin),
):
    return await admin_service.get_node_metrics(chain)
