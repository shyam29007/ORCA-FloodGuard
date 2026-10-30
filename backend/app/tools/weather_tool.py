"""Weather telemetry and precipitation forecast retrieval tool with explicit timestamp semantics."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.weather import WeatherForecastData
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus, EvidenceQuality


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

    # Attempt live API call if configured
    if settings.WEATHER_API_BASE_URL:
        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = client.get(
                    f"{settings.WEATHER_API_BASE_URL}/forecast",
                    params={"lat": latitude, "lon": longitude},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    r24 = float(data.get("rain_24h_mm", 0.0))
                    r48 = float(data.get("rain_48h_mm", r24 * 1.5))
                    r72 = float(data.get("rain_72h_mm", r48 * 1.3))

                    forecast = WeatherForecastData(
                        rainfall_24h_mm=r24,
                        rainfall_48h_mm=r48,
                        rainfall_72h_mm=r72,
                        precipitation_probability=float(data.get("prob", 70.0)),
                        temperature_c=float(data.get("temp", 28.5)),
                        forecast_source="IMD_LIVE",
                        forecast_issue_time=now,
                        forecast_valid_time_24h=valid_24h,
                        forecast_valid_time_48h=valid_48h,
                        forecast_valid_time_72h=valid_72h,
                        issued_at=now,
                        is_simulated=False,
                    )
                    ev24 = EvidenceRecordSchema(
                        source="IMD",
                        source_type="WEATHER_API",
                        location={"lat": latitude, "lon": longitude, "district": district},
                        parameter="rainfall_24h",
                        value=r24,
                        unit="mm",
                        observed_at=now,
                        forecast_issue_time=now,
                        forecast_valid_time=valid_24h,
                        retrieved_at=now,
                        status=EvidenceStatus.LIVE,
                        quality=EvidenceQuality.HIGH,
                        limitations="Numerical Weather Prediction (NWP) model output; convective rainfall may vary locally.",
                    )
                    evidence_records.append(ev24)
                    return forecast, evidence_records
        except Exception as e:
            logger.warning("Weather API request failed: %s; using simulated Punjab forecast.", str(e))

    # Standard fallback simulation (representative Punjab monsoon cloudburst scenario)
    base_rain = 58.0 if district and "jalandhar" in district.lower() else 42.0
    r24 = base_rain
    r48 = round(base_rain * 1.7, 1)
    r72 = round(base_rain * 2.4, 1)

    status = EvidenceStatus.SIMULATED if allow_simulated else EvidenceStatus.UNAVAILABLE

    forecast = WeatherForecastData(
        rainfall_24h_mm=r24 if allow_simulated else None,
        rainfall_48h_mm=r48 if allow_simulated else None,
        rainfall_72h_mm=r72 if allow_simulated else None,
        precipitation_probability=85.0 if allow_simulated else 0.0,
        temperature_c=27.4,
        wind_speed_kmh=18.5,
        forecast_source="IMD_MONSOON_SYNTHETIC",
        forecast_issue_time=now,
        forecast_valid_time_24h=valid_24h,
        forecast_valid_time_48h=valid_48h,
        forecast_valid_time_72h=valid_72h,
        issued_at=now,
        is_simulated=True,
    )

    # 24h Horizon Evidence Record
    ev24 = EvidenceRecordSchema(
        source="IMD_PUNJAB_RADAR",
        source_type="WEATHER_API",
        location={"lat": latitude, "lon": longitude, "district": district},
        parameter="rainfall_24h",
        value=r24 if allow_simulated else None,
        unit="mm",
        observed_at=now,
        forecast_issue_time=now,
        forecast_valid_time=valid_24h,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        limitations="Simulated monsoon scenario for demonstration when live radar feed is unconfigured.",
    )
    evidence_records.append(ev24)

    # 48h Horizon Evidence Record
    ev48 = EvidenceRecordSchema(
        source="IMD_PUNJAB_RADAR",
        source_type="WEATHER_API",
        location={"lat": latitude, "lon": longitude, "district": district},
        parameter="rainfall_48h",
        value=r48 if allow_simulated else None,
        unit="mm",
        observed_at=now,
        forecast_issue_time=now,
        forecast_valid_time=valid_48h,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        limitations="Simulated 48h accumulated monsoon forecast.",
    )
    evidence_records.append(ev48)

    # 72h Horizon Evidence Record
    ev72 = EvidenceRecordSchema(
        source="IMD_PUNJAB_RADAR",
        source_type="WEATHER_API",
        location={"lat": latitude, "lon": longitude, "district": district},
        parameter="rainfall_72h",
        value=r72 if allow_simulated else None,
        unit="mm",
        observed_at=now,
        forecast_issue_time=now,
        forecast_valid_time=valid_72h,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        limitations="Simulated 72h accumulated monsoon forecast.",
    )
    evidence_records.append(ev72)

    return forecast, evidence_records
