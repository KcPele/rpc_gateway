"""Tests for admin chain CRUD endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient

from fastapi_app.database import Chain, User
from tests.conftest import auth_headers, create_jwt_token, seed_chain, seed_user


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


def _chain_dict(chain: Chain) -> dict:
    """Convert a Chain document to the response dict format."""
    return {
        "id": str(chain.id),
        "name": chain.name,
        "chain_id": chain.chain_id,
        "is_enabled": chain.is_enabled,
        "admin_notes": chain.admin_notes,
        "created_at": chain.created_at,
        "updated_at": chain.updated_at,
    }


class TestListChains:
    """Tests for GET /admin/chains."""

    @pytest.mark.asyncio
    async def test_list_chains_with_data(
        self, http_client: AsyncClient, admin_token: str, mongo_client
    ):
        """Listing chains returns all chains."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            mock_chain = AsyncMock()
            mock_chain.id = "mock-id-1"
            mock_chain.name = "ethereum"
            mock_chain.chain_id = "1"
            mock_chain.is_enabled = True
            mock_chain.admin_notes = None
            mock_chain.created_at = datetime.now(timezone.utc)
            mock_chain.updated_at = datetime.now(timezone.utc)

            mock_sort = AsyncMock()
            mock_sort.to_list = AsyncMock(return_value=[mock_chain])
            MockChain.find().sort.return_value = mock_sort

            response = await http_client.get(
                "/admin/chains", headers=auth_headers(admin_token)
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "ethereum"

    @pytest.mark.asyncio
    async def test_list_chains_requires_auth(
        self, http_client: AsyncClient, user_token: str
    ):
        """Non-admin users can still list chains (auth required but not admin)."""
        response = await http_client.get(
            "/admin/chains", headers=auth_headers(user_token)
        )
        assert response.status_code == 200


class TestAddChain:
    """Tests for POST /admin/chains."""

    @pytest.mark.asyncio
    async def test_add_chain_success(self, http_client: AsyncClient, admin_token: str):
        """Admin can add a new chain."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=None)
            mock_instance = AsyncMock()
            mock_instance.id = "mock-id-123"
            mock_instance.name = "arbitrum"
            mock_instance.chain_id = "42161"
            mock_instance.is_enabled = True
            mock_instance.admin_notes = None
            mock_instance.created_at = datetime.now(timezone.utc)
            mock_instance.updated_at = datetime.now(timezone.utc)
            mock_instance.insert = AsyncMock()
            MockChain.return_value = mock_instance

            response = await http_client.post(
                "/admin/chains",
                json={"name": "arbitrum", "chainId": "42161", "isEnabled": True},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "arbitrum"

    @pytest.mark.asyncio
    async def test_add_chain_duplicate_name(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Adding a chain with a duplicate name returns 409."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            existing = AsyncMock()
            existing.name = "ethereum"
            MockChain.find_one = AsyncMock(return_value=existing)

            response = await http_client.post(
                "/admin/chains",
                json={"name": "ethereum", "chainId": "999"},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_add_chain_missing_fields(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Adding a chain without name or chainId returns 400."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=None)

            response = await http_client.post(
                "/admin/chains",
                json={"name": "only-name"},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_add_chain_non_admin_forbidden(
        self, http_client: AsyncClient, user_token: str
    ):
        """Non-admin cannot add a chain."""
        response = await http_client.post(
            "/admin/chains",
            json={"name": "forbidden", "chainId": "0"},
            headers=auth_headers(user_token),
        )
        assert response.status_code == 403


class TestUpdateChain:
    """Tests for PATCH /admin/chains/{chain_id}."""

    @pytest.mark.asyncio
    async def test_update_chain_name(self, http_client: AsyncClient, admin_token: str):
        """Admin can update a chain's name."""
        mock_chain = AsyncMock()
        mock_chain.name = "old-name"
        mock_chain.chain_id = "99"
        mock_chain.is_enabled = True
        mock_chain.admin_notes = None
        mock_chain.id = "mock-id"
        mock_chain.created_at = datetime.now(timezone.utc)
        mock_chain.updated_at = datetime.now(timezone.utc)
        mock_chain.save = AsyncMock()

        with patch("fastapi_app.services.admin.Chain") as MockChain:
            # First find_one for the chain being updated returns the chain
            # Second find_one for name conflict check returns None
            MockChain.find_one = AsyncMock(side_effect=[mock_chain, None])

            response = await http_client.patch(
                "/admin/chains/99",
                json={"name": "new-name"},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 200
            assert response.json()["data"]["name"] == "new-name"

    @pytest.mark.asyncio
    async def test_update_chain_disable(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Admin can disable a chain."""
        mock_chain = AsyncMock()
        mock_chain.name = "to-disable"
        mock_chain.chain_id = "88"
        mock_chain.is_enabled = True
        mock_chain.admin_notes = None
        mock_chain.id = "mock-id"
        mock_chain.created_at = datetime.now(timezone.utc)
        mock_chain.updated_at = datetime.now(timezone.utc)
        mock_chain.save = AsyncMock()

        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=mock_chain)

            response = await http_client.patch(
                "/admin/chains/88",
                json={"isEnabled": False},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 200
            assert response.json()["data"]["isEnabled"] is False

    @pytest.mark.asyncio
    async def test_update_chain_not_found(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Updating a non-existent chain returns 404."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=None)

            response = await http_client.patch(
                "/admin/chains/nonexistent",
                json={"name": "whatever"},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_chain_no_fields(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Updating with no fields returns 400."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=None)

            response = await http_client.patch(
                "/admin/chains/77",
                json={},
                headers=auth_headers(admin_token),
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_chain_non_admin(
        self, http_client: AsyncClient, user_token: str
    ):
        """Non-admin cannot update a chain."""
        response = await http_client.patch(
            "/admin/chains/66",
            json={"name": "hacked"},
            headers=auth_headers(user_token),
        )
        assert response.status_code == 403


class TestDeleteChain:
    """Tests for DELETE /admin/chains/{chain_id}."""

    @pytest.mark.asyncio
    async def test_delete_chain_success(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Admin can delete a chain."""
        mock_chain = AsyncMock()
        mock_chain.delete = AsyncMock()

        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=mock_chain)

            response = await http_client.delete(
                "/admin/chains/55", headers=auth_headers(admin_token)
            )
            assert response.status_code == 200
            assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_delete_chain_not_found(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Deleting a non-existent chain returns 404."""
        with patch("fastapi_app.services.admin.Chain") as MockChain:
            MockChain.find_one = AsyncMock(return_value=None)

            response = await http_client.delete(
                "/admin/chains/nonexistent", headers=auth_headers(admin_token)
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chain_non_admin(
        self, http_client: AsyncClient, user_token: str
    ):
        """Non-admin cannot delete a chain."""
        response = await http_client.delete(
            "/admin/chains/44", headers=auth_headers(user_token)
        )
        assert response.status_code == 403
