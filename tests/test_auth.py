"""Tests for auth endpoints: register, login, me, account, password, email, export."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from fastapi_app.database import User
from tests.conftest import (
    auth_headers,
    create_jwt_token,
    seed_app,
    seed_user,
)


class TestRegister:
    """Tests for POST /auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, http_client: AsyncClient):
        """Registering a new user returns 201 with token and user data."""
        response = await http_client.post(
            "/auth/register",
            json={"email": "newuser@example.com", "password": "securepass123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "token" in data["data"]
        assert data["data"]["user"]["email"] == "newuser@example.com"
        assert data["data"]["user"]["isAdmin"] is False
        assert data["data"]["user"]["isActive"] is True

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, http_client: AsyncClient, mongo_client
    ):
        """Registering with an existing email returns 409."""
        await seed_user(email="dup@example.com")
        response = await http_client.post(
            "/auth/register",
            json={"email": "dup@example.com", "password": "securepass123"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_short_password(self, http_client: AsyncClient):
        """Registering with a password shorter than 6 chars returns 422."""
        response = await http_client.post(
            "/auth/register",
            json={"email": "short@example.com", "password": "12345"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, http_client: AsyncClient):
        """Registering with an invalid email returns 422."""
        response = await http_client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "securepass123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_with_name(self, http_client: AsyncClient):
        """Registering with an optional name field succeeds."""
        response = await http_client.post(
            "/auth/register",
            json={
                "email": "named@example.com",
                "password": "securepass123",
                "name": "Test User",
            },
        )
        assert response.status_code == 201


class TestLogin:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, http_client: AsyncClient, mongo_client):
        """Login with correct credentials returns a token."""
        await seed_user(email="login@example.com", password="secret123")
        response = await http_client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "secret123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data["data"]
        assert data["data"]["user"]["email"] == "login@example.com"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, http_client: AsyncClient, mongo_client):
        """Login with wrong password returns 401."""
        await seed_user(email="wrong@example.com", password="correct")
        response = await http_client.post(
            "/auth/login",
            json={"email": "wrong@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, http_client: AsyncClient):
        """Login with a non-existent email returns 401."""
        response = await http_client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "secret"},
        )
        assert response.status_code == 401


class TestMe:
    """Tests for GET /auth/me."""

    @pytest.mark.asyncio
    async def test_me_returns_user(self, http_client: AsyncClient, mongo_client):
        """Authenticated GET /auth/me returns the current user."""
        user = await seed_user()
        token = create_jwt_token(str(user.id))
        response = await http_client.get("/auth/me", headers=auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_me_unauthorized(self, http_client: AsyncClient):
        """GET /auth/me without a token returns 401."""
        response = await http_client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, http_client: AsyncClient):
        """GET /auth/me with an invalid token returns 401."""
        response = await http_client.get(
            "/auth/me", headers=auth_headers("bogus.token.here")
        )
        assert response.status_code == 401


class TestAccount:
    """Tests for GET /auth/account."""

    @pytest.mark.asyncio
    async def test_account_returns_user(self, http_client: AsyncClient, mongo_client):
        """Authenticated GET /auth/account returns the current user."""
        user = await seed_user()
        token = create_jwt_token(str(user.id))
        response = await http_client.get("/auth/account", headers=auth_headers(token))
        assert response.status_code == 200
        assert response.json()["data"]["user"]["email"] == "test@example.com"


class TestUpdatePassword:
    """Tests for PATCH /auth/password."""

    @pytest.mark.asyncio
    async def test_update_password_success(
        self, http_client: AsyncClient, mongo_client
    ):
        """Updating password with correct current password succeeds."""
        user = await seed_user(password="oldpass123")
        token = create_jwt_token(str(user.id))
        response = await http_client.patch(
            "/auth/password",
            headers=auth_headers(token),
            json={"current_password": "oldpass123", "new_password": "newpass123"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_password_wrong_current(
        self, http_client: AsyncClient, mongo_client
    ):
        """Updating password with wrong current password returns 400."""
        user = await seed_user(password="oldpass123")
        token = create_jwt_token(str(user.id))
        response = await http_client.patch(
            "/auth/password",
            headers=auth_headers(token),
            json={"current_password": "wrongpass", "new_password": "newpass123"},
        )
        assert response.status_code == 400


class TestUpdateEmail:
    """Tests for PATCH /auth/email."""

    @pytest.mark.asyncio
    async def test_update_email_success(self, http_client: AsyncClient, mongo_client):
        """Updating email with correct password succeeds."""
        user = await seed_user(password="pass123")
        token = create_jwt_token(str(user.id))
        response = await http_client.patch(
            "/auth/email",
            headers=auth_headers(token),
            json={
                "email": "test@example.com",
                "new_email": "newemail@example.com",
                "password": "pass123",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_email_duplicate(self, http_client: AsyncClient, mongo_client):
        """Updating to an email already in use returns 409."""
        await seed_user(email="existing@example.com", password="pass123")
        user = await seed_user(email="changer@example.com", password="pass123")
        token = create_jwt_token(str(user.id))
        response = await http_client.patch(
            "/auth/email",
            headers=auth_headers(token),
            json={
                "email": "changer@example.com",
                "new_email": "existing@example.com",
                "password": "pass123",
            },
        )
        assert response.status_code == 409


class TestExport:
    """Tests for GET /auth/export."""

    @pytest.mark.asyncio
    async def test_export_user_data(self, http_client: AsyncClient, mongo_client):
        """Export returns user data and their apps."""
        user = await seed_user()
        await seed_app(user_id=str(user.id))
        token = create_jwt_token(str(user.id))
        response = await http_client.get("/auth/export", headers=auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data["data"]
        assert "apps" in data["data"]
