"""Tests for authentication, password hashing, JWT signing, and RBAC authorization."""

import pytest
from datetime import timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    require_role,
)
from backend.app.schemas.auth import UserRole, UserProfile


def test_password_hashing_and_verification():
    """PBKDF2-HMAC-SHA256 password hashing must verify valid password and reject invalid."""
    plain = "SecurePunjab@2026"
    hashed = hash_password(plain)
    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword@123", hashed) is False


def test_jwt_token_creation_and_decoding():
    """Valid JWT access token must decode to original payload."""
    payload = {"sub": "usr-123", "email": "test@orca.punjab.gov.in", "role": "OFFICIAL"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=30))
    decoded = decode_access_token(token)
    assert decoded["sub"] == "usr-123"
    assert decoded["email"] == "test@orca.punjab.gov.in"
    assert decoded["role"] == "OFFICIAL"


def test_jwt_tampered_token_rejected():
    """Tampered token with modified payload must be rejected."""
    token = create_access_token({"sub": "usr-123", "role": "CITIZEN"})
    parts = token.split(".")
    # Tamper the payload part
    tampered_token = f"{parts[0]}.eyJyZXBsYWNlZCI6InRhbXBlcmVkIn0.{parts[2]}"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered_token)
    assert exc_info.value.status_code == 401


def test_jwt_expired_token_rejected():
    """Expired token must be rejected with 401."""
    token = create_access_token({"sub": "usr-123"}, expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_api_login_successful_for_demo_accounts():
    """Pre-seeded evaluation accounts must log in successfully and return JWT."""
    client = TestClient(app)
    # Test Citizen login
    resp = client.post("/api/auth/login", json={"email": "citizen@orca.punjab.gov.in", "password": "Citizen@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "CITIZEN"

    # Test Official login
    resp_off = client.post("/api/auth/login", json={"email": "official@orca.punjab.gov.in", "password": "Official@123"})
    assert resp_off.status_code == 200
    assert resp_off.json()["user"]["role"] == "OFFICIAL"

    # Test Admin login
    resp_adm = client.post("/api/auth/login", json={"email": "admin@orca.punjab.gov.in", "password": "Admin@123"})
    assert resp_adm.status_code == 200
    assert resp_adm.json()["user"]["role"] == "ADMIN"


def test_api_login_invalid_password_returns_401():
    """Invalid credentials must return 401 Unauthorized."""
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "citizen@orca.punjab.gov.in", "password": "WrongPassword"})
    assert resp.status_code == 401


def test_api_register_and_login_new_user():
    """New user registration must succeed and allow subsequent login."""
    client = TestClient(app)
    new_email = "new_officer@orca.punjab.gov.in"
    reg_resp = client.post("/api/auth/register", json={
        "email": new_email,
        "full_name": "Kuldeep Singh",
        "password": "Password@999",
        "role": "OFFICIAL",
        "district": "Rupnagar",
    })
    assert reg_resp.status_code == 201
    assert "access_token" in reg_resp.json()

    # Login with new account
    login_resp = client.post("/api/auth/login", json={"email": new_email, "password": "Password@999"})
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["full_name"] == "Kuldeep Singh"


def test_api_demo_accounts_endpoint(monkeypatch):
    """GET /api/auth/demo-accounts returns evaluator accounts including restricted DEMO role, and disables in production."""
    client = TestClient(app)
    resp = client.get("/api/auth/demo-accounts")
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) >= 3
    roles = [a["role"] for a in accounts]
    assert "DEMO" in roles
    assert "CITIZEN" in roles
    assert "OFFICIAL" in roles
    assert "ADMIN" in roles

    # Verify production disables demo accounts endpoint
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "APP_ENV", "production")
    prod_resp = client.get("/api/auth/demo-accounts")
    assert prod_resp.status_code == 200
    assert prod_resp.json() == []


def test_api_demo_account_login_and_restricted_permissions(monkeypatch):
    """Restricted DEMO account logs in successfully but is rejected from official operations, and blocked in production."""
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "demo@orca.punjab.gov.in", "password": "Demo@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "DEMO"

    # Verify require_role forbids DEMO role on official actions
    demo_user = UserProfile(
        id=data["user"]["id"],
        email=data["user"]["email"],
        full_name=data["user"]["full_name"],
        role=UserRole.DEMO,
    )
    official_gate = require_role([UserRole.OFFICIAL, UserRole.ADMIN])
    with pytest.raises(HTTPException) as exc:
        official_gate(demo_user)
    assert exc.value.status_code == 403
    assert "Access denied" in exc.value.detail

    # Verify DEMO login is forbidden in production
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "APP_ENV", "production")
    prod_login = client.post("/api/auth/login", json={"email": "demo@orca.punjab.gov.in", "password": "Demo@123"})
    assert prod_login.status_code == 403
    assert "disabled in production" in prod_login.json()["detail"]


def test_require_role_rbac_enforcement():
    """require_role must allow permitted roles and raise 403 Forbidden on unpermitted."""
    official_user = UserProfile(id="1", email="off@test.com", full_name="Official", role=UserRole.OFFICIAL)
    citizen_user = UserProfile(id="2", email="cit@test.com", full_name="Citizen", role=UserRole.CITIZEN)

    checker = require_role([UserRole.OFFICIAL, UserRole.ADMIN])

    # Allowed
    result = checker(official_user)
    assert result.role == UserRole.OFFICIAL

    # Forbidden
    with pytest.raises(HTTPException) as exc:
        checker(citizen_user)
    assert exc.value.status_code == 403
    assert "Access denied" in exc.value.detail

