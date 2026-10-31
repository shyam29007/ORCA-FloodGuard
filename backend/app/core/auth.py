"""Cryptographic authentication, password hashing, and role-based access control (RBAC)."""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings
from backend.app.schemas.auth import UserRole, UserProfile

# JWT Secret Key
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET", "orca-floodguard-evaluation-secret-jwt-key-punjab-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = os.urandom(16)
    iterations = 100000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed string using constant-time digest comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_derived = bytes.fromhex(parts[3])
        actual_derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_derived, expected_derived)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(s: str) -> bytes:
    padding = b"=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii") + padding)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate cryptographically signed HMAC-SHA256 JWT access token."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload["exp"] = int(expire.timestamp())
    payload["iat"] = int(now.timestamp())

    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")

    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Validate and decode HMAC-SHA256 JWT access token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed JWT token.")

        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")

        expected_signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_signature = _base64url_decode(encoded_signature)

        if not hmac.compare_digest(actual_signature, expected_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature.")

        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp and exp < time.time():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")

        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token validation failed: {str(e)}")


# In-memory evaluation user store (pre-populated with evaluation accounts)
USERS_DATABASE: Dict[str, Dict[str, Any]] = {
    "demo@orca.punjab.gov.in": {
        "id": "usr-demo-001",
        "email": "demo@orca.punjab.gov.in",
        "full_name": "Evaluation Sandbox Observer (DEMO)",
        "password_hash": hash_password("Demo@123"),
        "role": UserRole.DEMO,
        "district": "Punjab State HQ (Evaluation Sandbox)",
        "created_at": datetime.now(timezone.utc),
    },
    "citizen@orca.punjab.gov.in": {
        "id": "usr-citizen-001",
        "email": "citizen@orca.punjab.gov.in",
        "full_name": "Gurpreet Singh (Citizen)",
        "password_hash": hash_password("Citizen@123"),
        "role": UserRole.CITIZEN,
        "district": "Jalandhar",
        "created_at": datetime.now(timezone.utc),
    },
    "field_officer@orca.punjab.gov.in": {
        "id": "usr-field-001",
        "email": "field_officer@orca.punjab.gov.in",
        "full_name": "Ravinder Singh (Field Officer)",
        "password_hash": hash_password("FieldOfficer@123"),
        "role": UserRole.FIELD_OFFICER,
        "district": "Shahkot Tehsil",
        "created_at": datetime.now(timezone.utc),
    },
    "official@orca.punjab.gov.in": {
        "id": "usr-official-001",
        "email": "official@orca.punjab.gov.in",
        "full_name": "Er. Harjit Kaur (SDMA Official)",
        "password_hash": hash_password("Official@123"),
        "role": UserRole.OFFICIAL,
        "district": "Punjab State HQ",
        "created_at": datetime.now(timezone.utc),
    },
    "admin@orca.punjab.gov.in": {
        "id": "usr-admin-001",
        "email": "admin@orca.punjab.gov.in",
        "full_name": "System Administrator",
        "password_hash": hash_password("Admin@123"),
        "role": UserRole.ADMIN,
        "district": "Chandigarh Central",
        "created_at": datetime.now(timezone.utc),
    },
}


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> UserProfile:
    """Retrieve and validate user identity from cryptographically signed JWT bearer token."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    user_id = payload.get("sub")
    email = payload.get("email")

    user_record = USERS_DATABASE.get(email)
    if not user_record:
        # Allow token-carried profile if user exists in token
        return UserProfile(
            id=user_id or "usr-unknown",
            email=email or "unknown@orca.local",
            full_name=payload.get("full_name", "Authenticated User"),
            role=UserRole(payload.get("role", "CITIZEN")),
            district=payload.get("district"),
        )

    return UserProfile(
        id=user_record["id"],
        email=user_record["email"],
        full_name=user_record["full_name"],
        role=user_record["role"],
        district=user_record["district"],
        created_at=user_record["created_at"],
    )


def require_role(allowed_roles: List[UserRole]):
    """Enforce role-based access control on sensitive endpoints."""
    def role_checker(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{user.role.value}' is not authorized to perform this operation. Required: {[r.value for r in allowed_roles]}",
            )
        return user

    return role_checker

