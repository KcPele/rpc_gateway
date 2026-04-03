"""Shared pytest fixtures for NodeBridge backend tests."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from fastapi_app.database import App, Chain, DefaultAppSettings, User
from fastapi_app.routes.auth import router as auth_router
from fastapi_app.routes.proxy import router as proxy_router
from fastapi_app.routes.apps import router as apps_router
from fastapi_app.routes.admin import router as admin_router

TEST_JWT_SECRET = "test-secret-key-for-testing-only-12345"
TEST_MONGO_URI = "mongodb://localhost:27017/test_nodebridge"


@pytest.fixture(autouse=True)
def override_settings():
    """Override environment variables for test isolation."""
    original_jwt = os.environ.get("JWT_SECRET")
    original_mongo = os.environ.get("MONGO_URI")
    os.environ["JWT_SECRET"] = TEST_JWT_SECRET
    os.environ["MONGO_URI"] = TEST_MONGO_URI
    yield
    if original_jwt:
        os.environ["JWT_SECRET"] = original_jwt
    elif "JWT_SECRET" in os.environ:
        del os.environ["JWT_SECRET"]
    if original_mongo:
        os.environ["MONGO_URI"] = original_mongo
    elif "MONGO_URI" in os.environ:
        del os.environ["MONGO_URI"]


@pytest.fixture(autouse=True)
def clear_rate_limit_buckets():
    """Clear rate limiter state between tests."""
    from fastapi_app.middleware import rate_limit

    rate_limit._buckets.clear()
    yield


@pytest.fixture(autouse=True)
def clear_api_key_cache():
    """Clear API key cache between tests."""
    from fastapi_app.middleware import api_key

    api_key._cached_apps.clear()
    api_key._pending_updates.clear()
    yield


def _make_test_app() -> FastAPI:
    """Create a FastAPI app without MongoDB lifespan for testing."""
    test_app = FastAPI(
        title="NodeBridge RPC Gateway (Test)",
        version="1.0.0",
    )
    test_app.include_router(auth_router, tags=["auth"])
    test_app.include_router(proxy_router, tags=["proxy"])
    test_app.include_router(apps_router, tags=["apps"])
    test_app.include_router(admin_router, tags=["admin"])

    @test_app.get("/")
    async def root():
        return {"name": "NodeBridge RPC Gateway", "version": "1.0.0"}

    @test_app.get("/health")
    async def health():
        return {"status": "healthy", "services": {"database": {"status": "healthy"}}}

    return test_app


@pytest_asyncio.fixture(scope="session")
async def mongo_client():
    """Create a mongomock-motor async client and initialize Beanie (session-scoped)."""
    client = AsyncMongoMockClient()
    db = client["test_nodebridge"]
    await init_beanie(
        database=db, document_models=[User, Chain, App, DefaultAppSettings]
    )
    yield client
    collections = await db.list_collection_names()
    for coll in collections:
        await db[coll].drop()


@pytest.fixture(autouse=True)
async def clean_db(mongo_client):
    """Clean the database before each test."""
    db = mongo_client["test_nodebridge"]
    collections = await db.list_collection_names()
    for coll in collections:
        await db[coll].drop()
    yield
    await init_beanie(
        database=db, document_models=[User, Chain, App, DefaultAppSettings]
    )
    yield client
    collections = await db.list_collection_names()
    for coll in collections:
        await db[coll].drop()


@pytest_asyncio.fixture
async def http_client(mongo_client) -> AsyncClient:
    """Create an httpx AsyncClient bound to a test FastAPI app (no real DB)."""
    test_app = _make_test_app()
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def create_jwt_token(user_id: str, secret: str = TEST_JWT_SECRET) -> str:
    """Helper to create a JWT token for a given user ID."""
    return jwt.encode(
        {"id": user_id, "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7},
        secret,
        algorithm="HS256",
    )


async def seed_user(
    email: str = "test@example.com",
    password: str = "password123",
    is_admin: bool = False,
    is_active: bool = True,
) -> User:
    """Create and return a test user."""
    user = User(
        email=email,
        password=User.hash_password(password),
        is_admin=is_admin,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await user.insert()
    return user


async def seed_chain(
    name: str = "ethereum",
    chain_id: str = "1",
    is_enabled: bool = True,
    admin_notes: str | None = None,
) -> Chain:
    """Create and return a test chain."""
    chain = Chain(
        name=name,
        chain_id=chain_id,
        is_enabled=is_enabled,
        admin_notes=admin_notes,
    )
    await chain.insert()
    return chain


async def seed_app(
    user_id: str,
    name: str = "Test App",
    chain_name: str = "ethereum",
    chain_id: str = "1",
    api_key: str | None = None,
    max_rps: int = 10,
    daily_requests_limit: int = 10000,
    is_active: bool = True,
) -> App:
    """Create and return a test app."""
    app_doc = App(
        name=name,
        description="A test app",
        user_id=user_id,
        chain_name=chain_name,
        chain_id=chain_id,
        api_key=api_key or str(uuid4()),
        max_rps=max_rps,
        daily_requests_limit=daily_requests_limit,
        is_active=is_active,
    )
    await app_doc.insert()
    return app_doc


def auth_headers(token: str) -> dict[str, str]:
    """Build Authorization headers from a JWT token."""
    return {"Authorization": f"Bearer {token}"}
