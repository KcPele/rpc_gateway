from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator

import motor.motor_asyncio
from beanie import Document, init_beanie
import bcrypt

from fastapi_app.config.settings import settings


class User(Document):
    email: str
    password: str
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Settings:
        name = "users"
        indexes = ["email"]

    def verify_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), self.password.encode())

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


class Chain(Document):
    name: str
    chain_id: str
    is_enabled: bool = True
    admin_notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Settings:
        name = "chains"
        indexes = ["name", "chain_id"]


class App(Document):
    name: str
    description: str | None = None
    user_id: str
    api_key: str
    chain_name: str
    chain_id: str
    max_rps: int
    daily_requests_limit: int
    requests: int = 0
    daily_requests: int = 0
    last_reset_date: datetime | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Settings:
        name = "apps"
        indexes = ["user_id", "api_key"]


class DefaultAppSettings(Document):
    max_rps: int
    daily_requests_limit: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Settings:
        name = "defaultappsettings"


client: motor.motor_asyncio.AsyncIOMotorClient | None = None


async def connect_to_mongo() -> motor.motor_asyncio.AsyncIOMotorClient:
    global client
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    db_name = "nodebridge"
    await init_beanie(
        database=client[db_name],
        document_models=[User, Chain, App, DefaultAppSettings],
    )
    return client


async def close_mongo() -> None:
    global client
    if client:
        client.close()
        client = None


async def health_check() -> dict:
    if not client:
        return {"status": "unhealthy", "error": "Not connected"}
    try:
        await client.admin.command("ping")
        return {"status": "healthy"}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


@asynccontextmanager
async def mongo_lifespan() -> AsyncGenerator[None, None]:
    await connect_to_mongo()
    try:
        yield
    finally:
        await close_mongo()
