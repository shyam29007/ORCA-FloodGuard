"""Dam telemetry, reservoir level, and spillway release schemas."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import Field, model_validator
from backend.app.schemas.common import BaseSchema
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus


class DamInformation(BaseSchema):
    """Dam metadata and reservoir telemetry."""
    dam_id: str
    name: str  # Bhakra Dam, Pong Dam, Ranjit Sagar Dam
    river: str  # Sutlej, Beas, Ravi
    full_reservoir_level_meters: float
    current_water_level_meters: Optional[float] = None
    capacity_percent: Optional[float] = None
    inflow_cusecs: Optional[float] = None
    outflow_discharge_cusecs: Optional[float] = None
    spillway_gates_open: Optional[int] = None
    status: EvidenceStatus = EvidenceStatus.LIVE
    is_simulated: bool = False
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_high_discharge: bool = False
    is_critical_discharge: bool = False

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


class DamAgentOutput(BaseSchema):
    """Normalized payload returned by Dam Agent."""
    relevant_dams: List[DamInformation] = Field(default_factory=list)
    max_downstream_discharge_cusecs: float = 0.0
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    status: str = "SUCCESS"
    notes: List[str] = Field(default_factory=list)
