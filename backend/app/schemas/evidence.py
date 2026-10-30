"""Evidence data structures and normalization contracts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import Field, field_validator
import uuid
from backend.app.schemas.common import BaseSchema


class EvidenceStatus(str, Enum):
    """Allowed evidence status levels as strictly required."""
    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"
    SIMULATED = "SIMULATED"
    STATIC_REFERENCE = "STATIC_REFERENCE"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceQuality(str, Enum):
    """Evidence confidence and sensor quality classification."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNCERTAIN = "UNCERTAIN"


class ExcludedEvidenceRecord(BaseSchema):
    """Details of an evidence record excluded from operational risk assessment."""
    evidence_id: str
    source: str
    parameter: str
    status: EvidenceStatus  # Preserves true source status (e.g. STATIC_REFERENCE, SIMULATED, LIVE)
    reason_for_exclusion: str
    eligibility_reason: Optional[str] = Field(default=None, description="Separate eligibility or exclusion classification")
    exclusion_reason: Optional[str] = Field(default=None, description="Machine-readable exclusion category")


class EvidenceRecordSchema(BaseSchema):
    """Normalized evidence record contract across all providers."""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = Field(..., description="Provider name (e.g., IMD, CWC, BBMB, NASA_SRTM, OSM)")
    source_type: str = Field(..., description="Type (e.g., WEATHER_API, RIVER_GAUGE, DAM_TELEMETRY, GIS)")
    location: Dict[str, Any] = Field(default_factory=dict, description="Geographic context (name, lat, lon, district)")
    parameter: str = Field(..., description="Physical parameter measured or forecast")
    value: Optional[Union[float, int, str, Dict[str, Any], List[Any]]] = Field(
        default=None, description="Measured or forecast value"
    )
    unit: str = Field(..., description="Engineering or physical unit (e.g., mm, m, cusecs, m_amsl)")
    
    # Explicit separated timestamp semantics
    observed_at: datetime = Field(..., description="Timestamp of physical sensor observation or provider issuance")
    forecast_issue_time: Optional[datetime] = Field(default=None, description="Timestamp when forecast model was run/issued")
    forecast_valid_time: Optional[datetime] = Field(default=None, description="Future timestamp or window target for forecast")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when our system fetched this record"
    )
    
    status: EvidenceStatus = Field(..., description="Verification status of this evidence")
    quality: EvidenceQuality = Field(default=EvidenceQuality.HIGH, description="Sensor/record quality")
    limitations: Optional[str] = Field(default=None, description="Known operational limitations or caveats")
    validation_flags: List[str] = Field(default_factory=list, description="Validation warnings or anomaly notes")

    # Geodetic & dataset provenance
    dataset_name: Optional[str] = Field(default=None, description="Official dataset identifier")
    dataset_version: Optional[str] = Field(default=None, description="Dataset release or mission version")
    spatial_resolution: Optional[str] = Field(default=None, description="Spatial resolution (e.g., 30m, 0.25deg)")
    vertical_datum: Optional[str] = Field(default=None, description="Vertical reference (e.g., EGM96 AMSL, MSL)")
    horizontal_datum: Optional[str] = Field(default=None, description="Horizontal reference (e.g., WGS84)")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper in EvidenceStatus.__members__:
                return EvidenceStatus[v_upper]
        return v

    @property
    def is_usable_for_risk(self) -> bool:
        """Determines if evidence can be considered authoritative for live risk calculations."""
        return self.status in (EvidenceStatus.LIVE, EvidenceStatus.HISTORICAL, EvidenceStatus.STATIC_REFERENCE, EvidenceStatus.SIMULATED) and self.value is not None


class EvidenceCollectionSummary(BaseSchema):
    """Aggregated status and counts of evidence collected for a run."""
    total_records: int = 0
    live_count: int = 0
    simulated_count: int = 0
    static_reference_count: int = 0
    stale_count: int = 0
    unavailable_count: int = 0
    critical_missing: List[str] = Field(default_factory=list)
    is_valid_for_assessment: bool = True
    sufficiency_status: str = "SUFFICIENT"
    validation_messages: List[str] = Field(default_factory=list)
    excluded_records: List[ExcludedEvidenceRecord] = Field(default_factory=list)
