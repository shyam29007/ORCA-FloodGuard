"""River gauge station and reading schemas."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import Field, model_validator
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
    is_simulated: bool = False
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_above_warning: bool = False
    is_above_danger: bool = False
    buffer_to_danger_meters: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def sync_simulated_status(cls, data: Any) -> Any:
        if isinstance(data, dict):
            status = data.get("status")
            status_str = status.value if hasattr(status, "value") else str(status or "")
            if status_str == "SIMULATED":
                data["is_simulated"] = True
            elif status_str in ("LIVE", "STATIC_REFERENCE", "UNAVAILABLE", "REJECTED"):
                data["is_simulated"] = False
            elif data.get("is_simulated") is True:
                data["status"] = EvidenceStatus.SIMULATED
        return data


class RiverAgentOutput(BaseSchema):
    """Normalized payload returned by River Agent."""
    nearest_station: Optional[RiverStation] = None
    latest_reading: Optional[RiverReading] = None
    distance_to_station_km: Optional[float] = None
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    status: str = "SUCCESS"
    notes: List[str] = Field(default_factory=list)
