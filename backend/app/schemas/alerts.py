"""Alert drafting, approval, and multi-channel dissemination schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema, RiskLevel


class AlertChannel(str, Enum):
    """Dissemination channels for flood warnings."""
    SMS = "SMS"
    VOICE_CALL = "VOICE_CALL"
    WHATSAPP = "WHATSAPP"
    CAP = "CAP"  # Common Alerting Protocol
    LOUDSPEAKER = "LOUDSPEAKER"


class AlertStatus(str, Enum):
    """Lifecycle status of an alert draft."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"


class AlertDraftSchema(BaseSchema):
    """Structured advisory draft prepared by Alert Agent."""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    village_id: str
    village_name: str
    risk_level: RiskLevel
    headline: str
    english_text: str
    punjabi_text: str
    recommended_action: str
    target_channels: List[AlertChannel] = Field(
        default_factory=lambda: [AlertChannel.SMS, AlertChannel.VOICE_CALL]
    )
    status: AlertStatus = AlertStatus.PENDING_APPROVAL
    evidence_summary: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class AlertApprovalRequest(BaseSchema):
    """Request by an authorized official to approve or reject an alert."""
    alert_id: str
    approved_by: str
    action: str = Field(..., description="APPROVE or REJECT")
    modification_notes: Optional[str] = None
    override_channels: Optional[List[AlertChannel]] = None


class AlertApprovalResponse(BaseSchema):
    """Response returned upon human approval action."""
    alert_id: str
    status: AlertStatus
    action_taken: str
    approved_by: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dispatch_results: Optional[Dict[str, Any]] = None

