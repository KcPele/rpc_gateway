"""Tests for admin management endpoints: users, apps, default settings."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from fastapi_app.database import App, Chain, DefaultAppSettings, User
from tests.conftest import (
    auth_headers,
    create_jwt_token,
    seed_app,
    seed_chain,
    seed_user,
)


@pytest_asyncio.fixture
async def admin_token(mongo_client) -> str:
    """Create an admin user and return their JWT token."""
    admin = await seed_user(is_admin=True)
    return create_jwt_token(str(admin.id))


@pytest_asyncio.fixture
async def user_token(mongo_client) -> str:
    """Create a non-admin user and return their JWT token."""
    user = await seed_user(is_admin=False)
    return create_jwt_token(str(user.id))


class TestAdminGetUsers:
    """Tests for GET /admin/users."""

    @pytest.mark.asyncio
    async def test_get_all_users(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can list all users with pagination."""
        await seed_user(email="user1@test.com")
        await seed_user(email="user2@test.com")
        response = await http_client.get(
            "/admin/users", headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "users" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_users_pagination(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can paginate users."""
        for i in range(5):
            await seed_user(email=f"page{i}@test.com")
        response = await http_client.get(
            "/admin/users?page=1&limit=2", headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["users"]) <= 2

    @pytest.mark.asyncio
    async def test_get_users_non_admin(self, http_client: AsyncClient, user_token: str):
        """Non-admin cannot list users."""
        response = await http_client.get(
            "/admin/users", headers=auth_headers(user_token)
        )
        assert response.status_code == 403


class TestAdminUpdateUser:
    """Tests for PATCH /admin/users/{user_id}."""

    @pytest.mark.asyncio
    async def test_update_user_email(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can update a user's email."""
        target = await seed_user(email="old@test.com")
        response = await http_client.patch(
            f"/admin/users/{str(target.id)}",
            json={"email": "new@test.com"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "new@test.com"

    @pytest.mark.asyncio
    async def test_update_user_is_active(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can deactivate a user."""
        target = await seed_user(email="active@test.com")
        response = await http_client.patch(
            f"/admin/users/{str(target.id)}",
            json={"is_active": False},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["isActive"] is False

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Updating a non-existent user returns 404."""
        response = await http_client.patch(
            "/admin/users/000000000000000000000000",
            json={"email": "ghost@test.com"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_non_admin(
        self, http_client: AsyncClient, user_token: str, mongo_client
    ):
        """Non-admin cannot update users."""
        target = await seed_user(email="protected@test.com")
        response = await http_client.patch(
            f"/admin/users/{str(target.id)}",
            json={"email": "hacked@test.com"},
            headers=auth_headers(user_token),
        )
        assert response.status_code == 403


class TestAdminGetApps:
    """Tests for GET /admin/apps."""

    @pytest.mark.asyncio
    async def test_get_all_apps(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can list all apps."""
        user = await seed_user(email="appowner@test.com")
        await seed_chain()
        await seed_app(user_id=str(user.id))
        response = await http_client.get(
            "/admin/apps", headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "apps" in data["data"]

    @pytest.mark.asyncio
    async def test_get_apps_filter_by_user(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can filter apps by user_id."""
        user = await seed_user(email="filterowner@test.com")
        await seed_chain()
        await seed_app(user_id=str(user.id))
        response = await http_client.get(
            f"/admin/apps?user_id={str(user.id)}", headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        for app_item in data["data"]["apps"]:
            assert app_item["userId"] == str(user.id)

    @pytest.mark.asyncio
    async def test_get_apps_non_admin(self, http_client: AsyncClient, user_token: str):
        """Non-admin cannot list all apps."""
        response = await http_client.get(
            "/admin/apps", headers=auth_headers(user_token)
        )
        assert response.status_code == 403


class TestAdminUpdateApp:
    """Tests for PATCH /admin/apps/{app_id}."""

    @pytest.mark.asyncio
    async def test_update_app_name(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can update an app's name."""
        user = await seed_user(email="appupdater@test.com")
        await seed_chain()
        app_doc = await seed_app(user_id=str(user.id), name="old-name")
        response = await http_client.patch(
            f"/admin/apps/{str(app_doc.id)}",
            json={"name": "new-name"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_app_not_found(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Updating a non-existent app returns 404."""
        response = await http_client.patch(
            "/admin/apps/000000000000000000000000",
            json={"name": "ghost"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_app_non_admin(
        self, http_client: AsyncClient, user_token: str, mongo_client
    ):
        """Non-admin cannot update apps."""
        user = await seed_user(email="applocked@test.com")
        await seed_chain()
        app_doc = await seed_app(user_id=str(user.id))
        response = await http_client.patch(
            f"/admin/apps/{str(app_doc.id)}",
            json={"name": "hacked"},
            headers=auth_headers(user_token),
        )
        assert response.status_code == 403


class TestDefaultAppSettings:
    """Tests for GET/PATCH /admin/default-app-settings."""

    @pytest.mark.asyncio
    async def test_get_default_settings_creates_if_missing(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Getting default settings creates them if they don't exist."""
        response = await http_client.get(
            "/admin/default-app-settings", headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "maxRps" in data["data"]
        assert "dailyRequestsLimit" in data["data"]

    @pytest.mark.asyncio
    async def test_update_default_settings(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can update default app settings."""
        await http_client.get(
            "/admin/default-app-settings", headers=auth_headers(admin_token)
        )
        response = await http_client.patch(
            "/admin/default-app-settings",
            json={"maxRps": 50, "dailyRequestsLimit": 50000},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["maxRps"] == 50
        assert data["data"]["dailyRequestsLimit"] == 50000

    @pytest.mark.asyncio
    async def test_update_default_settings_snake_case(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Admin can update settings using snake_case fields."""
        await http_client.get(
            "/admin/default-app-settings", headers=auth_headers(admin_token)
        )
        response = await http_client.patch(
            "/admin/default-app-settings",
            json={"max_rps": 100, "daily_requests_limit": 200000},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_settings_no_fields(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Updating with no fields returns 400."""
        await http_client.get(
            "/admin/default-app-settings", headers=auth_headers(admin_token)
        )
        response = await http_client.patch(
            "/admin/default-app-settings",
            json={},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_settings_non_admin(self, http_client: AsyncClient, user_token: str):
        """Non-admin cannot access default settings."""
        response = await http_client.get(
            "/admin/default-app-settings", headers=auth_headers(user_token)
        )
        assert response.status_code == 403
        response = await http_client.patch(
            "/admin/default-app-settings",
            json={"max_rps": 1},
            headers=auth_headers(user_token),
        )
        assert response.status_code == 403
