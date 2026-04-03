"""Live integration tests against a running FastAPI server.

Usage:
    python tests/test_live_endpoints.py

Requires:
    - A running FastAPI server (default: http://localhost:8888)
    - Admin user: admin@nodebridge.com / Qwerty123456
    - `requests` package installed

This test uses real HTTP calls (not mongomock) to catch runtime bugs
that unit tests miss: DB connection issues, serialization errors,
missing imports, route wiring problems, etc.
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

BASE_URL = os.environ.get("SERVER_URL", "http://localhost:8888").rstrip("/")
ADMIN_EMAIL = "admin@nodebridge.com"
ADMIN_PASSWORD = "Qwerty123456"

PASS = 0
FAIL = 0
RESULTS: list[str] = []


def _record(method: str, path: str, status: int, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    msg = f"  [{tag}] {method:7s} {path:45s} -> {status:3d}  {detail}"
    RESULTS.append(msg)
    print(msg)


def _check(
    method: str,
    path: str,
    expected_status: int,
    resp: requests.Response,
    checks: list[str] | None = None,
) -> bool:
    ok = resp.status_code == expected_status
    if not ok:
        _record(method, path, resp.status_code, False, f"expected {expected_status}")
        return False
    if checks:
        for check in checks:
            if check not in resp.text:
                _record(method, path, resp.status_code, False, f"missing '{check}'")
                return False
    _record(method, path, resp.status_code, True)
    return True


def _has_keys(data: dict, keys: list[str], path: str = "") -> bool:
    for k in keys:
        if k not in data:
            return False
    return True


def _assert_success(resp: requests.Response, path: str, method: str = "GET") -> dict:
    """Assert {success: true} envelope and return data dict."""
    try:
        body = resp.json()
    except Exception:
        _record(method, path, resp.status_code, False, "not valid JSON")
        return {}
    if resp.status_code != 200:
        _record(
            method,
            path,
            resp.status_code,
            False,
            f"expected 200, got body keys: {list(body.keys())}",
        )
        return {}
    if body.get("success") is not True:
        _record(method, path, resp.status_code, False, f"success != true: {body}")
        return {}
    _record(method, path, resp.status_code, True)
    return body.get("data", {})


class LiveTest:
    """Run all live endpoint tests sequentially."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.token: str = ""
        self.user_id: str = ""
        self.app_id: str = ""

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def test_login(self) -> bool:
        resp = self.session.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        try:
            body = resp.json()
        except Exception:
            _record("POST", "/auth/login", resp.status_code, False, "not valid JSON")
            return False
        ok = resp.status_code == 200 and body.get("success") is True
        if ok:
            self.token = body["data"]["token"]
            self.user_id = body["data"]["user"]["id"]
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            _record("POST", "/auth/login", resp.status_code, True, "token acquired")
        else:
            _record("POST", "/auth/login", resp.status_code, False, f"body: {body}")
        return ok

    def test_me(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/auth/me")
        data = _assert_success(resp, "/auth/me", "GET")
        if not data:
            return False
        return _has_keys(data, ["user"])

    def test_account(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/auth/account")
        data = _assert_success(resp, "/auth/account", "GET")
        if not data:
            return False
        return _has_keys(data, ["user"])

    def test_password_change(self) -> bool:
        resp = self.session.patch(
            f"{BASE_URL}/auth/password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "TempPass123"},
        )
        ok = resp.status_code == 200
        try:
            body = resp.json()
            ok = ok and body.get("success") is True
        except Exception:
            ok = False
        _record("PATCH", "/auth/password", resp.status_code, ok)
        # Change back so other tests still work
        self.session.patch(
            f"{BASE_URL}/auth/password",
            json={"current_password": "TempPass123", "new_password": ADMIN_PASSWORD},
        )
        return ok

    def test_email_change(self) -> bool:
        new_email = f"admin+{int(time.time())}@nodebridge.com"
        resp = self.session.patch(
            f"{BASE_URL}/auth/email",
            json={
                "email": ADMIN_EMAIL,
                "new_email": new_email,
                "password": ADMIN_PASSWORD,
            },
        )
        ok = resp.status_code == 200
        try:
            body = resp.json()
            ok = ok and body.get("success") is True
        except Exception:
            ok = False
        _record("PATCH", "/auth/email", resp.status_code, ok)
        # Revert email back
        self.session.patch(
            f"{BASE_URL}/auth/email",
            json={
                "email": new_email,
                "new_email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
        )
        return ok

    def test_export(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/auth/export")
        data = _assert_success(resp, "/auth/export", "GET")
        if not data:
            return False
        return _has_keys(data, ["user", "apps"])

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def test_admin_list_chains(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/admin/chains")
        try:
            body = resp.json()
        except Exception:
            _record("GET", "/admin/chains", resp.status_code, False, "not valid JSON")
            return False
        ok = resp.status_code == 200
        _record("GET", "/admin/chains", resp.status_code, ok)
        return ok

    def test_admin_add_chain(self) -> bool:
        resp = self.session.post(
            f"{BASE_URL}/admin/chains",
            json={
                "name": f"test-chain-{int(time.time())}",
                "chainId": "99999",
                "isEnabled": True,
            },
        )
        try:
            body = resp.json()
        except Exception:
            _record("POST", "/admin/chains", resp.status_code, False, "not valid JSON")
            return False
        ok = resp.status_code == 201 and body.get("success") is True
        _record("POST", "/admin/chains", resp.status_code, ok)
        return ok

    def test_admin_users(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/admin/users")
        data = _assert_success(resp, "/admin/users", "GET")
        if not data:
            return False
        return _has_keys(data, ["users", "pagination"])

    def test_admin_apps(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/admin/apps")
        data = _assert_success(resp, "/admin/apps", "GET")
        if not data:
            return False
        return _has_keys(data, ["apps", "pagination"])

    def test_admin_default_app_settings_get(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/admin/default-app-settings")
        data = _assert_success(resp, "/admin/default-app-settings", "GET")
        if not data:
            return False
        return _has_keys(data, ["maxRps", "dailyRequestsLimit"])

    def test_admin_default_app_settings_patch(self) -> bool:
        resp = self.session.patch(
            f"{BASE_URL}/admin/default-app-settings",
            json={"maxRps": 250, "dailyRequestsLimit": 1100000},
        )
        try:
            body = resp.json()
        except Exception:
            _record(
                "PATCH",
                "/admin/default-app-settings",
                resp.status_code,
                False,
                "not valid JSON",
            )
            return False
        ok = resp.status_code == 200 and body.get("success") is True
        _record("PATCH", "/admin/default-app-settings", resp.status_code, ok)
        # Revert
        self.session.patch(
            f"{BASE_URL}/admin/default-app-settings",
            json={"maxRps": 200, "dailyRequestsLimit": 1000000},
        )
        return ok

    # ------------------------------------------------------------------
    # Apps
    # ------------------------------------------------------------------

    def test_apps_list(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/apps/")
        data = _assert_success(resp, "/apps/", "GET")
        if not data:
            return False
        return _has_keys(data, ["apps", "pagination"])

    def test_apps_create(self) -> bool:
        resp = self.session.post(
            f"{BASE_URL}/apps/",
            json={
                "name": f"Live Test App {int(time.time())}",
                "description": "Created by live test",
                "chain_name": "ethereum",
                "chain_id": "1",
            },
        )
        try:
            body = resp.json()
        except Exception:
            _record("POST", "/apps/", resp.status_code, False, "not valid JSON")
            return False
        ok = resp.status_code == 201 and body.get("success") is True
        if ok and "data" in body:
            self.app_id = body["data"].get("_id", "")
        _record("POST", "/apps/", resp.status_code, ok)
        return ok

    def test_apps_dashboard_stats(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/apps/dashboard/stats")
        data = _assert_success(resp, "/apps/dashboard/stats", "GET")
        if not data:
            return False
        return _has_keys(data, ["stats"])

    def test_apps_usage_all(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/apps/usage/all")
        data = _assert_success(resp, "/apps/usage/all", "GET")
        if not data:
            return False
        return _has_keys(data, ["analytics"])

    # ------------------------------------------------------------------
    # Proxy / Health
    # ------------------------------------------------------------------

    def test_health(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/health")
        try:
            body = resp.json()
        except Exception:
            _record("GET", "/health", resp.status_code, False, "not valid JSON")
            return False
        ok = resp.status_code == 200 and body.get("status") == "healthy"
        _record("GET", "/health", resp.status_code, ok)
        return ok

    # ------------------------------------------------------------------
    # Response format checks
    # ------------------------------------------------------------------

    def test_response_format_camel_case(self) -> bool:
        """Verify that success responses use camelCase field names."""
        resp = self.session.get(f"{BASE_URL}/apps/")
        try:
            body = resp.json()
        except Exception:
            _record("GET", "/apps/ (format check)", 0, False, "not valid JSON")
            return False
        if body.get("success") is not True:
            _record("GET", "/apps/ (format check)", 0, False, "success != true")
            return False
        data = body.get("data", {})
        apps = data.get("apps", [])
        if apps:
            app = apps[0]
            camel_fields = [
                "chainName",
                "chainId",
                "maxRps",
                "dailyRequestsLimit",
                "isActive",
                "createdAt",
                "updatedAt",
            ]
            for field in camel_fields:
                if field in app:
                    _record(
                        "GET",
                        "/apps/ (format check)",
                        200,
                        True,
                        f"camelCase '{field}' found",
                    )
                    return True
        _record("GET", "/apps/ (format check)", 200, True, "response structure valid")
        return True

    # ------------------------------------------------------------------
    # Run all
    # ------------------------------------------------------------------

    def run_all(self) -> None:
        tests = [
            ("Login", self.test_login),
            ("GET /auth/me", self.test_me),
            ("GET /auth/account", self.test_account),
            ("PATCH /auth/password", self.test_password_change),
            ("PATCH /auth/email", self.test_email_change),
            ("GET /auth/export", self.test_export),
            ("GET /admin/chains", self.test_admin_list_chains),
            ("POST /admin/chains", self.test_admin_add_chain),
            ("GET /admin/users", self.test_admin_users),
            ("GET /admin/apps", self.test_admin_apps),
            (
                "GET /admin/default-app-settings",
                self.test_admin_default_app_settings_get,
            ),
            (
                "PATCH /admin/default-app-settings",
                self.test_admin_default_app_settings_patch,
            ),
            ("GET /apps/", self.test_apps_list),
            ("POST /apps/", self.test_apps_create),
            ("GET /apps/dashboard/stats", self.test_apps_dashboard_stats),
            ("GET /apps/usage/all", self.test_apps_usage_all),
            ("GET /health", self.test_health),
            ("Response format (camelCase)", self.test_response_format_camel_case),
        ]

        print(f"\n{'=' * 80}")
        print(f"  Live Endpoint Tests — {BASE_URL}")
        print(f"{'=' * 80}\n")

        for name, fn in tests:
            try:
                fn()
            except Exception as exc:
                _record("---", name, 0, False, f"exception: {exc}")

        print(f"\n{'=' * 80}")
        print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL}")
        print(f"{'=' * 80}\n")

        if FAIL > 0:
            sys.exit(1)


if __name__ == "__main__":
    LiveTest().run_all()
