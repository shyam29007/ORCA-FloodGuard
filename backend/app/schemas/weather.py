"""Weather schema definitions for rainfall forecasts and precipitation evidence."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import Field
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


class WeatherAgentOutput(BaseSchema):
    """Normalized payload returned by Weather Agent."""
    forecast: WeatherForecastData
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    status: str = "SUCCESS"
    notes: List[str] = Field(default_factory=list)
