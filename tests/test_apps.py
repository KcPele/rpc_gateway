"""Tests for app management endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from fastapi_app.database import App, Chain, User
from tests.conftest import (
    auth_headers,
    create_jwt_token,
    seed_app,
    seed_chain,
    seed_user,
)


@pytest_asyncio.fixture
async def user_token(mongo_client) -> str:
    """Create a user and return their JWT token. Also seeds a chain."""
    await seed_chain(name="ethereum", chain_id="1")
    user = await seed_user(email="appuser@test.com")
    return create_jwt_token(str(user.id)), str(user.id)


class TestCreateApp:
    """Tests for POST /apps/."""

    @pytest.mark.asyncio
    async def test_create_app_success(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Creating an app with valid data returns 201."""
        token, user_id = user_token
        response = await http_client.post(
            "/apps/",
            json={
                "name": "My App",
                "description": "A test application",
                "chain_name": "ethereum",
                "chain_id": "1",
            },
            headers=auth_headers(token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "My App"
        assert data["data"]["chain_name"] == "ethereum"

    @pytest.mark.asyncio
    async def test_create_app_chain_not_found(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Creating an app for a non-existent chain returns 404."""
        token, user_id = user_token
        response = await http_client.post(
            "/apps/",
            json={
                "name": "Bad App",
                "chain_name": "nonexistent",
                "chain_id": "999",
            },
            headers=auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_app_unauthorized(
        self, http_client: AsyncClient, mongo_client
    ):
        """Creating an app without auth returns 401."""
        await seed_chain(name="ethereum", chain_id="1")
        response = await http_client.post(
            "/apps/",
            json={
                "name": "No Auth App",
                "chain_name": "ethereum",
                "chain_id": "1",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_app_max_limit(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Creating more than 5 apps for a user returns 403."""
        token, user_id = user_token
        for i in range(5):
            await seed_app(
                user_id=user_id,
                name=f"App {i}",
                chain_name="ethereum",
                chain_id="1",
            )
        response = await http_client.post(
            "/apps/",
            json={
                "name": "Sixth App",
                "chain_name": "ethereum",
                "chain_id": "1",
            },
            headers=auth_headers(token),
        )
        assert response.status_code == 403


class TestGetUserApps:
    """Tests for GET /apps/."""

    @pytest.mark.asyncio
    async def test_get_user_apps_pagination(
        self, http_client: AsyncClient, mongo_client
    ):
        """Pagination parameters work correctly."""
        await seed_chain(name="ethereum", chain_id="1")
        user = await seed_user(email="paginated@test.com")
        for i in range(5):
            await seed_app(user_id=str(user.id), name=f"Page App {i}")
        token = create_jwt_token(str(user.id))
        response = await http_client.get(
            "/apps/?page=1&limit=2", headers=auth_headers(token)
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["apps"]) == 2
        assert data["data"]["pagination"]["current_page"] == 1


class TestDashboardStats:
    """Tests for GET /apps/dashboard/stats."""

    @pytest.mark.asyncio
    async def test_dashboard_stats(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Dashboard returns stats for the user's apps."""
        token, user_id = user_token
        await seed_app(user_id=user_id, name="Stat App")
        response = await http_client.get(
            "/apps/dashboard/stats", headers=auth_headers(token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        stats = data["data"]["stats"]
        assert stats["total_apps"] == 1
        assert "max_apps" in stats


class TestGetSingleApp:
    """Tests for GET /apps/{app_id}."""

    @pytest.mark.asyncio
    async def test_get_app_with_key(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Getting a single app returns it with the API key visible."""
        token, user_id = user_token
        app_doc = await seed_app(user_id=user_id)
        response = await http_client.get(
            f"/apps/{str(app_doc.id)}", headers=auth_headers(token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data["data"]

    @pytest.mark.asyncio
    async def test_get_app_not_found(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Getting a non-existent app returns 404."""
        token, user_id = user_token
        response = await http_client.get(
            "/apps/000000000000000000000000", headers=auth_headers(token)
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_app_access_denied(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """User cannot access another user's app."""
        token, user_id = user_token
        other_user = await seed_user(email="other@test.com")
        other_app = await seed_app(user_id=str(other_user.id))
        response = await http_client.get(
            f"/apps/{str(other_app.id)}", headers=auth_headers(token)
        )
        assert response.status_code == 404


class TestUpdateApp:
    """Tests for PATCH /apps/{app_id}."""

    @pytest.mark.asyncio
    async def test_update_app_name(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """User can update their app's name."""
        token, user_id = user_token
        app_doc = await seed_app(user_id=user_id, name="old-name")
        response = await http_client.patch(
            f"/apps/{str(app_doc.id)}",
            json={"name": "new-name"},
            headers=auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "new-name"

    @pytest.mark.asyncio
    async def test_update_app_description(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """User can update their app's description."""
        token, user_id = user_token
        app_doc = await seed_app(user_id=user_id)
        response = await http_client.patch(
            f"/apps/{str(app_doc.id)}",
            json={"description": "Updated description"},
            headers=auth_headers(token),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_app_not_found(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Updating a non-existent app returns 404."""
        token, user_id = user_token
        response = await http_client.patch(
            "/apps/000000000000000000000000",
            json={"name": "ghost"},
            headers=auth_headers(token),
        )
        assert response.status_code == 404


class TestDeleteApp:
    """Tests for DELETE /apps/{app_id}."""

    @pytest.mark.asyncio
    async def test_delete_app_success(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """User can delete their own app."""
        token, user_id = user_token
        app_doc = await seed_app(user_id=user_id)
        response = await http_client.delete(
            f"/apps/{str(app_doc.id)}", headers=auth_headers(token)
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_delete_app_not_found(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Deleting a non-existent app returns 404."""
        token, user_id = user_token
        response = await http_client.delete(
            "/apps/000000000000000000000000", headers=auth_headers(token)
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_app_access_denied(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """User cannot delete another user's app."""
        token, user_id = user_token
        other_user = await seed_user(email="deleteother@test.com")
        other_app = await seed_app(user_id=str(other_user.id))
        response = await http_client.delete(
            f"/apps/{str(other_app.id)}", headers=auth_headers(token)
        )
        assert response.status_code == 404


class TestRegenerateKey:
    """Tests for POST /apps/{app_id}/regenerate-key."""

    @pytest.mark.asyncio
    async def test_regenerate_key(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Regenerating an API key returns a new UUID."""
        token, user_id = user_token
        app_doc = await seed_app(user_id=user_id, api_key="original-key")
        response = await http_client.post(
            f"/apps/{str(app_doc.id)}/regenerate-key", headers=auth_headers(token)
        )
        assert response.status_code == 200
        new_key = response.json()["data"]
        assert new_key != "original-key"
        assert len(new_key) > 0


class TestAppUsage:
    """Tests for GET /apps/{app_id}/usage and GET /apps/usage/all."""

    @pytest.mark.asyncio
    async def test_single_app_usage(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Getting usage for a single app returns analytics."""
        token, user_id = user_token
        app_doc = await seed_app(user_id=user_id)
        response = await http_client.get(
            f"/apps/{str(app_doc.id)}/usage", headers=auth_headers(token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "analytics" in data["data"]
        assert "hourly_breakdown" in data["data"]["analytics"]

    @pytest.mark.asyncio
    async def test_all_apps_usage(
        self, http_client: AsyncClient, user_token, mongo_client
    ):
        """Getting all apps usage returns a summary with per-app data."""
        token, user_id = user_token
        await seed_app(user_id=user_id, name="Usage App 1")
        await seed_app(user_id=user_id, name="Usage App 2")
        response = await http_client.get("/apps/usage/all", headers=auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "analytics" in data["data"]
        assert "summary" in data["data"]["analytics"]
        assert "apps" in data["data"]["analytics"]
