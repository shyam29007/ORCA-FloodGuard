"""Weather schema definitions for rainfall forecasts and precipitation evidence."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import Field, model_validator
from backend.app.schemas.common import BaseSchema
from backend.app.schemas.evidence import EvidenceRecordSchema


class WeatherForecastData(BaseSchema):
    """Cumulative rainfall and atmospheric conditions for 24, 48, and 72-hour horizons."""
    rainfall_24h_mm: Optional[float] = Field(default=None, description="Predicted 24h rainfall in mm; null if unavailable")
    rainfall_48h_mm: Optional[float] = Field(default=None, description="Predicted cumulative 48h rainfall in mm; null if unavailable")
    rainfall_72h_mm: Optional[float] = Field(default=None, description="Predicted cumulative 72h rainfall in mm; null if unavailable")
    precipitation_probability: float = Field(0.0, ge=0.0, le=100.0, description="Probability percentage")
    temperature_c: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    forecast_source: str = "IMD_WEATHER"
    forecast_issue_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    forecast_valid_time_24h: Optional[datetime] = None
    forecast_valid_time_48h: Optional[datetime] = None
    forecast_valid_time_72h: Optional[datetime] = None
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_simulated: bool = False

    @model_validator(mode="before")
    @classmethod
    def sync_simulated_status(cls, data: Any) -> Any:
        if isinstance(data, dict):
            src = str(data.get("forecast_source", ""))
            if "SIMULATED" in src or "SAMPLE" in src or data.get("is_simulated") is True:
                data["is_simulated"] = True
            elif src in ("IMD", "IMD_WEATHER", "IMD_API", "LIVE"):
                data["is_simulated"] = False
        return data


class WeatherAgentOutput(BaseSchema):
    """Normalized payload returned by Weather Agent."""
    forecast: WeatherForecastData
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    status: str = "SUCCESS"
    notes: List[str] = Field(default_factory=list)
