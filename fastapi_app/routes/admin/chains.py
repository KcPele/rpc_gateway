from __future__ import annotations

from fastapi import APIRouter, Depends, status

from fastapi_app.middleware.admin import require_admin
from fastapi_app.middleware.auth import get_current_user
from fastapi_app.services import admin as admin_service

router = APIRouter(tags=["admin-chains"])


@router.get("/chains")
async def list_chains(user=Depends(get_current_user)):
    return await admin_service.list_chains()


@router.post("/chains", status_code=status.HTTP_201_CREATED)
async def add_chain(payload: dict, user=Depends(require_admin)):
    return await admin_service.add_chain(payload)


@router.patch("/chains/{chain_id}")
async def update_chain(chain_id: str, payload: dict, user=Depends(require_admin)):
    return await admin_service.update_chain(chain_id, payload)


@router.delete("/chains/{chain_id}")
async def delete_chain(chain_id: str, user=Depends(require_admin)):
    return await admin_service.delete_chain(chain_id)
