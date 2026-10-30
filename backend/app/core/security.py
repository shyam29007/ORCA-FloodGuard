"""Security utilities and API key verification (where required)."""

from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """Verify optional API key for protected routes or human approval actions."""
    # In development mode, open access by default
    if settings.APP_ENV == "development":
        return api_key or "dev-user"

    # In production, check key if configured
    configured_key = getattr(settings, "ADMIN_API_KEY", None)
    if configured_key and api_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key or "authenticated-user"

