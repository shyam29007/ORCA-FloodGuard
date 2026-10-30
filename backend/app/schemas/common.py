"""Common schemas and API response wrappers."""

from datetime import datetime, timezone
from enum import Enum
from typing import Generic, Optional, TypeVar, Any, Dict
from pydantic import BaseModel, ConfigDict, Field
import uuid

T = TypeVar("T")


class RiskLevel(str, Enum):
    """Deterministic flood risk levels."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class BaseSchema(BaseModel):
    """Base Pydantic schema with standard datetime and ORM configurations."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ApiResponse(BaseSchema, Generic[T]):
    """Standardized API response envelope."""
    success: bool = True
    message: str = "Operation successful"
    data: Optional[T] = None
    errors: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Coordinates(BaseSchema):
    """Geographic coordinate pair."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")

