from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from fastapi_app.config.settings import settings
from fastapi_app.database import close_mongo, connect_to_mongo, health_check
from fastapi_app.routes.auth import router as auth_router
from fastapi_app.routes.proxy import router as proxy_router
from fastapi_app.routes.apps import router as apps_router
from fastapi_app.routes.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect_to_mongo()
    yield
    await close_mongo()


app = FastAPI(
    title="NodeBridge RPC Gateway",
    version="1.0.0",
    description="Multi-tenant RPC gateway for node access",
    lifespan=lifespan,
)

# Register routers (routers already include their own path prefixes)
app.include_router(auth_router, tags=["auth"])
app.include_router(proxy_router, tags=["proxy"])
app.include_router(apps_router, tags=["apps"])
app.include_router(admin_router, tags=["admin"])


@app.get("/")
async def root():
    return {
        "name": "NodeBridge RPC Gateway",
        "version": "1.0.0",
        "description": "Multi-tenant RPC gateway for node access",
    }


@app.get("/health")
async def health():
    db_health = await health_check()
    import resource

    mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {
        "status": "healthy",
        "services": {
            "database": db_health,
            "memory_mb": round(mem_usage, 2),
        },
    }
