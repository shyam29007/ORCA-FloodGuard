"""Weather telemetry and precipitation forecast retrieval tool with explicit timestamp semantics."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List
from backend.app.core.logging import logger
from backend.app.schemas.weather import WeatherForecastData
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus, EvidenceQuality
from backend.app.integrations.imd_provider import IMDWeatherProvider


def fetch_weather_forecast(
    latitude: float,
    longitude: float,
    district: Optional[str] = None,
    allow_simulated: bool = True,
) -> Tuple[WeatherForecastData, List[EvidenceRecordSchema]]:
    """Retrieve 24/48/72-hour precipitation forecast with distinct observation and valid timestamps."""
    now = datetime.now(timezone.utc)
    valid_24h = now + timedelta(hours=24)
    valid_48h = now + timedelta(hours=48)
    valid_72h = now + timedelta(hours=72)
    evidence_records: List[EvidenceRecordSchema] = []

    # 1. Attempt live API retrieval via IMDWeatherProvider if configured
    provider = IMDWeatherProvider()
    if provider.is_configured():
        try:
            return provider.fetch_forecast(latitude=latitude, longitude=longitude, district=district)
        except Exception as e:
            logger.warning("IMD weather provider failed: %s; falling back according to simulation configuration.", str(e))

    # 2. Fallback: Simulation or Explicit UNAVAILABLE
    base_rain = 58.0 if district and "jalandhar" in district.lower() else 42.0
    r24 = base_rain if allow_simulated else None
    r48 = round(base_rain * 1.7, 1) if allow_simulated else None
    r72 = round(base_rain * 2.4, 1) if allow_simulated else None

    status = EvidenceStatus.SIMULATED if allow_simulated else EvidenceStatus.UNAVAILABLE
    source_name = "IMD_PUNJAB_RADAR" if allow_simulated else "IMD"

    forecast = WeatherForecastData(
        rainfall_24h_mm=r24,
        rainfall_48h_mm=r48,
        rainfall_72h_mm=r72,
        precipitation_probability=85.0 if allow_simulated else 0.0,
        temperature_c=27.4 if allow_simulated else 0.0,
        wind_speed_kmh=18.5 if allow_simulated else 0.0,
        forecast_source="IMD_MONSOON_SYNTHETIC" if allow_simulated else "IMD_UNAVAILABLE",
        forecast_issue_time=now,
        forecast_valid_time_24h=valid_24h,
        forecast_valid_time_48h=valid_48h,
        forecast_valid_time_72h=valid_72h,
        issued_at=now,
        is_simulated=allow_simulated,
    )

    # 24h Horizon Evidence Record
    ev24 = EvidenceRecordSchema(
        source=source_name,
        source_type="WEATHER_API",
        location={"lat": latitude, "lon": longitude, "district": district},
        parameter="rainfall_24h",
        value=r24,
        unit="mm",
        observed_at=now,
        forecast_issue_time=now,
        forecast_valid_time=valid_24h,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        dataset_name="IMD Radar / NWP Model",
        limitations="Simulated monsoon scenario for demonstration when live radar feed is unconfigured." if allow_simulated else "Live telemetry feed is unconfigured or unavailable.",
        eligibility_reason="SIMULATION_DEMO" if allow_simulated else "MEASUREMENT_UNAVAILABLE",
    )
    evidence_records.append(ev24)

    # 48h Horizon Evidence Record
    ev48 = EvidenceRecordSchema(
        source=source_name,
        source_type="WEATHER_API",
        location={"lat": latitude, "lon": longitude, "district": district},
        parameter="rainfall_48h",
        value=r48,
        unit="mm",
        observed_at=now,
        forecast_issue_time=now,
        forecast_valid_time=valid_48h,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        dataset_name="IMD Radar / NWP Model",
        limitations="Simulated 48h accumulated monsoon forecast." if allow_simulated else "Live telemetry feed is unconfigured or unavailable.",
        eligibility_reason="SIMULATION_DEMO" if allow_simulated else "MEASUREMENT_UNAVAILABLE",
    )
    evidence_records.append(ev48)

    # 72h Horizon Evidence Record
    ev72 = EvidenceRecordSchema(
        source=source_name,
        source_type="WEATHER_API",
        location={"lat": latitude, "lon": longitude, "district": district},
        parameter="rainfall_72h",
        value=r72,
        unit="mm",
        observed_at=now,
        forecast_issue_time=now,
        forecast_valid_time=valid_72h,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        dataset_name="IMD Radar / NWP Model",
        limitations="Simulated 72h accumulated monsoon forecast." if allow_simulated else "Live telemetry feed is unconfigured or unavailable.",
        eligibility_reason="SIMULATION_DEMO" if allow_simulated else "MEASUREMENT_UNAVAILABLE",
    )
    evidence_records.append(ev72)

    return forecast, evidence_records
