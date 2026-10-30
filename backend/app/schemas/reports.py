"""Citizen and ground observation report schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema


class ReportStatus(str, Enum):
    """Review and verification status of a ground report."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"


class ResidentReportCreate(BaseSchema):
    """Citizen upload request describing observed flooding."""
    village_name: str
    latitude: float
    longitude: float
    water_level_inches: Optional[float] = Field(None, ge=0.0)
    observations: str
    reporter_name: Optional[str] = "Anonymous Citizen"
    contact_phone: Optional[str] = None
    media_url: Optional[str] = None


class ResidentReportReviewRequest(BaseSchema):
    """Review action by disaster management official."""
    status: ReportStatus
    reviewer_name: str
    review_notes: Optional[str] = None
    confidence_weight: float = Field(1.0, ge=0.0, le=1.0)


class ResidentReportResponse(BaseSchema):
    """Structured response for resident report query."""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    village_name: str
    latitude: float
    longitude: float
    water_level_inches: Optional[float] = None
    observations: str
    reporter_name: Optional[str] = None
    media_url: Optional[str] = None
    status: ReportStatus = ReportStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

