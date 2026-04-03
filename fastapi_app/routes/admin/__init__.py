from __future__ import annotations

from fastapi import APIRouter

from fastapi_app.routes.admin.chains import router as chains_router
from fastapi_app.routes.admin.management import router as management_router
from fastapi_app.routes.admin.nodes import router as nodes_router

router = APIRouter(prefix="/admin")

router.include_router(nodes_router)
router.include_router(chains_router)
router.include_router(management_router)
