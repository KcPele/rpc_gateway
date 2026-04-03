"""Tests for proxy execution/consensus routes with mocked HTTP."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from fastapi_app.database import App, Chain, User
from fastapi_app.config.settings import ChainConfig
from tests.conftest import seed_app, seed_chain, seed_user


@pytest_asyncio.fixture
async def client_with_chain(http_client: AsyncClient, mongo_client):
    """Provide a client with a seeded chain, user, and app."""
    await seed_chain(name="ethereum", chain_id="1")
    user = await seed_user(email="proxy@test.com")
    app_doc = await seed_app(
        user_id=str(user.id),
        chain_name="ethereum",
        chain_id="1",
        api_key="test-api-key-12345",
        max_rps=100,
        daily_requests_limit=1000000,
    )
    return http_client, app_doc


def _make_chain_config(exec_urls=None, cons_urls=None, prom_urls=None):
    """Helper to create a ChainConfig."""
    return ChainConfig(
        execution_rpc_url=exec_urls,
        consensus_api_url=cons_urls,
        prometheus_url=prom_urls,
    )


class TestProxyExecution:
    """Tests for POST /{chain}/exec/{key}/{path}."""

    @pytest.mark.asyncio
    async def test_proxy_exec_no_chain_config(self, http_client: AsyncClient):
        """Proxying to an unconfigured chain returns 404."""
        response = await http_client.post(
            "/fakechain/exec/somekey/",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_proxy_exec_success(self, client_with_chain):
        """Proxying execution RPC forwards the request and returns the response."""
        http_client, app_doc = client_with_chain

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b'{"jsonrpc":"2.0","result":"0x123","id":1}'
        mock_response.headers = {"content-type": "application/json"}

        chain_config = _make_chain_config(exec_urls=["http://localhost:8545"])

        with patch("fastapi_app.routes.proxy._async_client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)

            with patch(
                "fastapi_app.routes.proxy.settings",
            ) as mock_settings:
                mock_settings.get_chain_config.return_value = chain_config

                response = await http_client.post(
                    "/ethereum/exec/test-api-key-12345/",
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_blockNumber",
                        "params": [],
                        "id": 1,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["result"] == "0x123"

    @pytest.mark.asyncio
    async def test_proxy_exec_invalid_api_key(self, client_with_chain):
        """Proxying with an invalid API key returns 403."""
        http_client, _ = client_with_chain

        chain_config = _make_chain_config(exec_urls=["http://localhost:8545"])

        with patch(
            "fastapi_app.routes.proxy.settings",
        ) as mock_settings:
            mock_settings.get_chain_config.return_value = chain_config

            response = await http_client.post(
                "/ethereum/exec/wrong-key/",
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                },
            )
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_proxy_exec_chain_mismatch(self, client_with_chain):
        """Proxying with an API key for a different chain returns 403."""
        http_client, app_doc = client_with_chain

        chain_config = _make_chain_config(exec_urls=["http://localhost:8546"])

        with patch(
            "fastapi_app.routes.proxy.settings",
        ) as mock_settings:
            mock_settings.get_chain_config.return_value = chain_config

            response = await http_client.post(
                "/polygon/exec/test-api-key-12345/",
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                },
            )
            assert response.status_code == 403


class TestProxyConsensus:
    """Tests for GET /{chain}/cons/{key}/{path}."""

    @pytest.mark.asyncio
    async def test_proxy_cons_no_chain_config(self, http_client: AsyncClient):
        """Proxying consensus to an unconfigured chain returns 404."""
        response = await http_client.get("/fakechain/cons/somekey/eth/v1/node/health")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_proxy_cons_success(self, client_with_chain):
        """Proxying consensus API forwards the request and returns the response."""
        http_client, app_doc = client_with_chain

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b'{"data":{"is_syncing":false,"head_slot":"100"}}'
        mock_response.headers = {"content-type": "application/json"}

        chain_config = _make_chain_config(cons_urls=["http://localhost:5052"])

        with patch("fastapi_app.routes.proxy._async_client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)

            with patch(
                "fastapi_app.routes.proxy.settings",
            ) as mock_settings:
                mock_settings.get_chain_config.return_value = chain_config

                response = await http_client.get(
                    "/ethereum/cons/test-api-key-12345/eth/v1/node/health"
                )
                assert response.status_code == 200


class TestProxyHealth:
    """Tests for GET /health/{chain}."""

    @pytest.mark.asyncio
    async def test_proxy_health_chain_not_found(self, http_client: AsyncClient):
        """Health check for an unconfigured chain returns 404."""
        response = await http_client.get("/health/unknown")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_proxy_health_success_with_mocks(self, http_client: AsyncClient):
        """Health check returns structured data when HTTP is mocked."""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        chain_config = _make_chain_config(
            exec_urls=["http://localhost:8545"],
            cons_urls=["http://localhost:5052"],
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=None)
            instance.post.return_value = mock_response
            instance.get.return_value = mock_response
            mock_client_cls.return_value = instance

            with patch(
                "fastapi_app.routes.proxy.settings",
            ) as mock_settings:
                mock_settings.get_chain_config.return_value = chain_config

                response = await http_client.get("/health/eth")
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert "chain" in data
                assert "checks" in data
