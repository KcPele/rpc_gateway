"""Tests for admin node health/metrics endpoints with mocked HTTP."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from fastapi_app.database import User
from tests.conftest import auth_headers, create_jwt_token, seed_user


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


class TestNodeHealth:
    """Tests for GET /admin/node-health/{chain}."""

    @pytest.mark.asyncio
    async def test_node_health_no_chain_config(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Requesting health for an unconfigured chain returns 404."""
        response = await http_client.get(
            "/admin/node-health/nonexistent", headers=auth_headers(admin_token)
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_node_health_with_mocks(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Node health returns structured data when HTTP is mocked."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": False}
        mock_response.text = "go_goroutines 42"

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=None)
            instance.post.return_value = mock_response
            instance.get.return_value = mock_response
            mock_client.return_value = instance

            with patch.dict(
                "os.environ",
                {
                    "JWT_SECRET": "test-secret-key-for-testing-only-12345",
                    "MONGO_URI": "mongodb://localhost:27017/test_nodebridge",
                    "ETH_EXECUTION_RPC_URL": "http://localhost:8545",
                    "ETH_CONSENSUS_API_URL": "http://localhost:5052",
                    "ETH_PROMETHEUS_URL": "http://localhost:9090",
                },
            ):
                response = await http_client.get(
                    "/admin/node-health/eth", headers=auth_headers(admin_token)
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "execution" in data["data"]
                assert "consensus" in data["data"]
                assert "overall" in data["data"]

    @pytest.mark.asyncio
    async def test_node_health_non_admin(
        self, http_client: AsyncClient, user_token: str
    ):
        """Non-admin cannot access node health."""
        response = await http_client.get(
            "/admin/node-health/eth", headers=auth_headers(user_token)
        )
        assert response.status_code == 403


class TestNodeMetrics:
    """Tests for GET /admin/node-metrics/{chain}."""

    @pytest.mark.asyncio
    async def test_node_metrics_no_prometheus_config(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Requesting metrics for a chain without Prometheus returns 404."""
        response = await http_client.get(
            "/admin/node-metrics/nonexistent", headers=auth_headers(admin_token)
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_node_metrics_with_mocks(
        self, http_client: AsyncClient, admin_token: str
    ):
        """Node metrics returns structured data when HTTP is mocked."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "go_goroutines 42\ngo_gc_cycles_total_gc_cycles_total 100"

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=None)
            instance.get.return_value = mock_response
            mock_client.return_value = instance

            with patch.dict(
                "os.environ",
                {
                    "JWT_SECRET": "test-secret-key-for-testing-only-12345",
                    "MONGO_URI": "mongodb://localhost:27017/test_nodebridge",
                    "ETH_EXECUTION_RPC_URL": "http://localhost:8545",
                    "ETH_CONSENSUS_API_URL": "http://localhost:5052",
                    "ETH_PROMETHEUS_URL": "http://localhost:9090",
                },
            ):
                response = await http_client.get(
                    "/admin/node-metrics/eth", headers=auth_headers(admin_token)
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "totalNodes" in data["data"]

    @pytest.mark.asyncio
    async def test_node_metrics_non_admin(
        self, http_client: AsyncClient, user_token: str
    ):
        """Non-admin cannot access node metrics."""
        response = await http_client.get(
            "/admin/node-metrics/eth", headers=auth_headers(user_token)
        )
        assert response.status_code == 403
