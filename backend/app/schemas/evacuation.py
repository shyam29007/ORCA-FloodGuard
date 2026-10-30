"""Relief centre, evacuation route, and hazard avoidance schemas."""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema
from backend.app.schemas.evidence import EvidenceRecordSchema


class RouteVerificationStatus(str, Enum):
    """Safety verification status of evacuation corridors."""
    CANDIDATE = "CANDIDATE"
    UNVERIFIED = "UNVERIFIED"
    VERIFIED_OPEN = "VERIFIED_OPEN"
    REPORTED_BLOCKED = "REPORTED_BLOCKED"
    UNAVAILABLE = "UNAVAILABLE"
    # Legacy backward compatibility alias
    VERIFIED_SAFE = "VERIFIED_OPEN"
    PASSABLE_WITH_CAUTION = "CANDIDATE"
    IMPASSABLE_FLOODED = "REPORTED_BLOCKED"


class RouteInspectionEvidence(BaseSchema):
    """Verifiable field inspection evidence authorizing VERIFIED_OPEN status."""
    inspection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    route_id: str
    authorized_source: str = Field(..., description="e.g., Punjab DDMA Field Team, SDM Inspection, Traffic Police")
    inspection_timestamp: datetime
    current_status: RouteVerificationStatus
    inspector_name_or_id: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    limitations: Optional[str] = None


class ReliefCentreSchema(BaseSchema):
    """Shelter and relief camp information."""
    relief_centre_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    district: str
    latitude: float
    longitude: float
    elevation_meters: Optional[float] = None
    capacity_persons: int = 500
    current_occupancy: Optional[int] = Field(default=None, description="Verified live occupancy; null for registered reference facilities")
    available_capacity: Optional[int] = Field(default=None, description="Verified available capacity; null for registered reference facilities")
    is_live_verified: bool = Field(default=False, description="True only if live telemetry or field verification confirms occupancy")
    verification_status: str = Field(default="REGISTERED_REFERENCE", description="REGISTERED_REFERENCE or LIVE_VERIFIED")
    contact_phone: Optional[str] = None
    facilities: List[str] = Field(default_factory=list)  # Food, Medical, Water, Power Backup
    is_active: bool = True
    distance_km: Optional[float] = None


class EvacuationRouteSchema(BaseSchema):
    """Candidate evacuation route linking a village to a relief facility."""
    route_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origin_village_id: str
    destination_relief_centre_id: str
    route_name: str
    distance_km: float
    estimated_time_minutes: int
    verification_status: RouteVerificationStatus = RouteVerificationStatus.CANDIDATE
    elevation_profile: Dict[str, Any] = Field(default_factory=dict)
    known_hazards: List[str] = Field(default_factory=list)
    waypoints: List[Dict[str, float]] = Field(default_factory=list)
    verification_notes: Optional[str] = None
    inspection: Optional[RouteInspectionEvidence] = None


class GISEvacuationAgentOutput(BaseSchema):
    """Output returned by GIS & Evacuation Agent."""
    village_elevation_meters: Optional[float] = None
    elevation_discrepancy_warning: Optional[str] = None
    is_low_lying_zone: bool = False
    nearest_relief_centres: List[ReliefCentreSchema] = Field(default_factory=list)
    evacuation_routes: List[EvacuationRouteSchema] = Field(default_factory=list)
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    status: str = "SUCCESS"
    notes: List[str] = Field(default_factory=list)
