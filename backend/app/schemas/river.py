"""River gauge station and reading schemas."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import Field
from backend.app.schemas.common import BaseSchema
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus


class RiverStation(BaseSchema):
    """River gauge monitoring station metadata."""
    station_id: str
    station_name: str
    river_name: str  # Sutlej, Beas, Ravi, Ghaggar
    district: str
    latitude: float
    longitude: float
    warning_level_meters: float
    danger_level_meters: float
    highest_flood_level_meters: Optional[float] = None


class RiverReading(BaseSchema):
    """Specific reading or status report from a river station."""
    station_id: str
    water_level_meters: Optional[float] = None
    discharge_cusecs: Optional[float] = None
    trend: str = Field("STABLE", description="RISING, FALLING, STABLE, or UNKNOWN")
    status: EvidenceStatus = EvidenceStatus.LIVE
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_above_warning: bool = False
    is_above_danger: bool = False
    buffer_to_danger_meters: Optional[float] = None


class RiverAgentOutput(BaseSchema):
    """Normalized payload returned by River Agent."""
    nearest_station: Optional[RiverStation] = None
    latest_reading: Optional[RiverReading] = None
    distance_to_station_km: Optional[float] = None
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    status: str = "SUCCESS"
    notes: List[str] = Field(default_factory=list)

