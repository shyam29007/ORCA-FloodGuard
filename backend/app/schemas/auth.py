"""Authentication and authorization schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from backend.app.schemas.common import BaseSchema


class UserRole(str, Enum):
    """Hierarchical role-based access control roles."""
    CITIZEN = "CITIZEN"
    FIELD_OFFICER = "FIELD_OFFICER"
    OFFICIAL = "OFFICIAL"
    ADMIN = "ADMIN"
    DEMO = "DEMO"


class UserRegisterRequest(BaseSchema):
    """User registration payload."""
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User full name")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")
    role: UserRole = Field(default=UserRole.CITIZEN, description="Assigned role")
    district: Optional[str] = Field(None, description="Assigned Punjab district or jurisdiction")


class UserLoginRequest(BaseSchema):
    """User login payload."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserProfile(BaseSchema):
    """Sanitized user identity without secrets."""
    id: str
    email: str
    full_name: str
    role: UserRole
    district: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TokenResponse(BaseSchema):
    """JWT bearer token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile

