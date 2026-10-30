"""Flood risk levels and assessment contracts."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema, Coordinates, RiskLevel
from backend.app.schemas.location import VillageLocation
from backend.app.schemas.evidence import EvidenceRecordSchema, ExcludedEvidenceRecord
from backend.app.schemas.evacuation import GISEvacuationAgentOutput
from backend.app.schemas.alerts import AlertDraftSchema


class RiskOutlook(BaseSchema):
    """Forecast window outlook for 24h, 48h, or 72h."""
    horizon: str = Field(..., description="24h, 48h, or 72h")
    risk_level: RiskLevel
    # Calibrated statistical confidence removed; marked uncalibrated unless calibrated model exists
    confidence_status: str = Field("NOT_CALIBRATED", description="Calibration status (e.g. NOT_CALIBRATED)")
    confidence_score: Optional[float] = Field(default=None, description="Only populated if an authoritative calibration methodology exists")
    confidence: Optional[float] = Field(default=None, description="Legacy backward-compatibility field")
    primary_factors: List[str] = Field(default_factory=list)
    triggered_rules: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    rainfall_forecast_mm: Optional[float] = Field(default=None, description="Forecast rainfall in mm, or None if unavailable")
    river_proximity_risk: str = "NORMAL"
    dam_discharge_risk: str = "NORMAL"


class FloodAssessmentRequest(BaseSchema):
    """Request payload to assess flood risk for a village."""
    village_name: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    district: Optional[str] = None
    forecast_horizon_hours: int = Field(72, description="24, 48, or 72 hours")
    include_simulated_fallback: bool = Field(
        True, description="Allow SIMULATED evidence for scenario exploration/demonstration"
    )
    operational_mode: bool = Field(
        False, description="When true, strictly requires LIVE critical telemetry and forbids simulated alerts"
    )


class FloodAssessmentResponse(BaseSchema):
    """Comprehensive, transparent flood assessment response."""
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    village: VillageLocation
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_risk: RiskLevel
    outlooks: Dict[str, RiskOutlook] = Field(default_factory=dict)
    
    # Rigorous decoupled validation & sufficiency reporting
    schema_validation_status: str = Field("PASSED", description="Schema & structure syntax validation")
    evidence_sufficiency_status: str = Field("SUFFICIENT", description="SUFFICIENT_LIVE, SIMULATED_ONLY, or INSUFFICIENT_EVIDENCE")
    assessment_mode: str = Field("OPERATIONAL", description="OPERATIONAL or SIMULATION_DEMO")
    assessment_status: str = Field("OPERATIONAL", description="OPERATIONAL, SIMULATED_DEMO, or INSUFFICIENT_EVIDENCE")
    
    # Unbiased confidence reporting
    confidence_status: str = Field("NOT_CALIBRATED", description="Explicit calibration state")
    confidence_score: Optional[float] = Field(default=None, description="Calibrated score; null when using deterministic rules")
    
    # Evidence provenance
    contributing_evidence: List[EvidenceRecordSchema] = Field(default_factory=list)
    excluded_evidence: List[ExcludedEvidenceRecord] = Field(default_factory=list)
    triggered_rules: List[str] = Field(default_factory=list)
    explanation: str
    
    evacuation: Optional[GISEvacuationAgentOutput] = None
    alert_draft_id: Optional[str] = None
    alert_draft: Optional[AlertDraftSchema] = None
    
    limitations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Legacy field
    validation_status: str = Field("PASSED", description="Legacy status field")
