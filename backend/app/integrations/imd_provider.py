"""IMD (India Meteorological Department) Weather and Precipitation Provider Adapter."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any
from dateutil import parser as dt_parser

from backend.app.integrations.base import BaseLiveDataProvider
from backend.app.core.config import settings
from backend.app.schemas.weather import WeatherForecastData
from backend.app.schemas.evidence import (
    EvidenceRecordSchema,
    EvidenceStatus,
    EvidenceQuality,
)


def parse_to_utc(ts: Any, default: Optional[datetime] = None) -> datetime:
    """Parse string or datetime to UTC-aware datetime."""
    if ts is None:
        return default or datetime.now(timezone.utc)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, str):
        try:
            parsed = dt_parser.parse(ts)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return default or datetime.now(timezone.utc)
    return default or datetime.now(timezone.utc)


class IMDWeatherProvider(BaseLiveDataProvider):
    """Adapter for retrieving official rainfall telemetry and forecasts from IMD."""

    service_type = "Weather & Precipitation Telemetry"
    verified_official_endpoint = "https://api.imd.gov.in/public/api_reference.html"
    access_restriction = (
        "Institutional access restricted under IMD Data Policy; requires static IP whitelisting on IMD gateway "
        "and OAuth 2.0 Bearer JWT token from /api/oauth/token.php."
    )
    requires_authentication = True
    freshness_max_hours = settings.WEATHER_FRESHNESS_MAX_HOURS
    expected_credential_names = ["IMD_API_KEY", "IMD_BEARER_JWT", "IP_WHITELIST"]
    health_check_endpoint = "/forecast"
    health_check_params = {"lat": 31.0267, "lon": 75.7871, "district": "Jalandhar"}
    dependent_agent_name = "Weather Agent"
    impact_description = "Live rainfall and weather evidence unavailable."
    fallback_description = "SIMULATED data, if DEMO mode is enabled; INSUFFICIENT_EVIDENCE if OPERATIONAL mode."

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        super().__init__(
            provider_name="IMD",
            base_url=base_url or settings.WEATHER_API_BASE_URL,
            api_key=api_key or settings.IMD_API_KEY,
            timeout=timeout,
        )

    def _validate_health_payload(self, data: Dict[str, Any]) -> Tuple[bool, bool, Optional[str], Dict[str, Any]]:
        """Validate IMD response payload structure and determine if live telemetry is present."""
        if not isinstance(data, dict):
            return False, False, None, {"error": "Expected JSON object dictionary."}

        has_rain_key = any(k in data for k in ("rain_24h_mm", "rainfall_24h_mm", "forecast", "rainfall", "rain"))
        if not has_rain_key:
            return False, False, None, {"error": "Missing expected rainfall/forecast fields in payload."}

        r24 = data.get("rain_24h_mm")
        if r24 is None:
            r24 = data.get("rainfall_24h_mm")

        obs_ts_str = data.get("observed_at") or data.get("issue_time") or data.get("timestamp")
        parsed_obs = parse_to_utc(obs_ts_str) if obs_ts_str else None

        now = datetime.now(timezone.utc)
        is_fresh = False
        if parsed_obs:
            age_hours = (now - parsed_obs).total_seconds() / 3600.0
            max_fresh = getattr(self, "freshness_max_hours", settings.WEATHER_FRESHNESS_MAX_HOURS)
            is_fresh = 0 <= age_hours <= max_fresh

        has_meas = (r24 is not None)
        has_live_data = has_meas and is_fresh
        latest_ts = parsed_obs.isoformat() if parsed_obs else None

        diag = {
            "rainfall_24h_mm": r24,
            "has_measurements": has_meas,
            "observed_at": latest_ts,
            "is_fresh": is_fresh,
            "district": data.get("district", "Jalandhar"),
        }
        return True, has_live_data, latest_ts, diag

    def _normalize_payload(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        district: Optional[str] = None,
    ) -> Tuple[WeatherForecastData, List[EvidenceRecordSchema]]:
        """Normalize raw IMD API payload into typed domain schemas and evidence records."""
        now = datetime.now(timezone.utc)

        # Parse timestamps
        issue_time = parse_to_utc(data.get("issue_time") or data.get("observed_at"), default=now)
        observed_at = parse_to_utc(data.get("observed_at"), default=issue_time)

        valid_24h = parse_to_utc(data.get("valid_time_24h"), default=issue_time + timedelta(hours=24))
        valid_48h = parse_to_utc(data.get("valid_time_48h"), default=issue_time + timedelta(hours=48))
        valid_72h = parse_to_utc(data.get("valid_time_72h"), default=issue_time + timedelta(hours=72))

        # Extract measurements safely; NEVER convert None to 0.0!
        r24 = float(data["rain_24h_mm"]) if data.get("rain_24h_mm") is not None else None
        r48 = float(data["rain_48h_mm"]) if data.get("rain_48h_mm") is not None else None
        r72 = float(data["rain_72h_mm"]) if data.get("rain_72h_mm") is not None else None

        prob_val = data.get("prob") or data.get("precipitation_probability")
        prob = float(prob_val) if prob_val is not None else 70.0

        temp_val = data.get("temp") or data.get("temperature_c")
        temp = float(temp_val) if temp_val is not None else 28.5

        wind_val = data.get("wind_speed_kmh") or data.get("wind_kmh")
        wind = float(wind_val) if wind_val is not None else None

        forecast = WeatherForecastData(
            rainfall_24h_mm=r24,
            rainfall_48h_mm=r48,
            rainfall_72h_mm=r72,
            precipitation_probability=prob,
            temperature_c=temp,
            wind_speed_kmh=wind,
            forecast_source="IMD_LIVE",
            forecast_issue_time=issue_time,
            forecast_valid_time_24h=valid_24h,
            forecast_valid_time_48h=valid_48h,
            forecast_valid_time_72h=valid_72h,
            issued_at=issue_time,
            is_simulated=False,
        )

        evidence_records: List[EvidenceRecordSchema] = []
        loc_dict = {"lat": latitude, "lon": longitude}
        if district:
            loc_dict["district"] = district

        # 24h Horizon Evidence Record
        ev24 = EvidenceRecordSchema(
            source="IMD",
            source_type="WEATHER_API",
            location=loc_dict,
            parameter="rainfall_24h",
            value=r24,
            unit="mm",
            observed_at=observed_at,
            forecast_issue_time=issue_time,
            forecast_valid_time=valid_24h,
            retrieved_at=now,
            status=EvidenceStatus.LIVE if r24 is not None else EvidenceStatus.UNAVAILABLE,
            quality=EvidenceQuality.HIGH if r24 is not None else EvidenceQuality.LOW,
            dataset_name="IMD Quantitative Precipitation Forecast (QPF)",
            source_url=f"{self.base_url}/forecast",
            limitations="Numerical Weather Prediction (NWP) model output; convective rainfall may vary locally.",
            eligibility_reason="LIVE_IMD_TELEMETRY" if r24 is not None else "MEASUREMENT_UNAVAILABLE",
        )
        evidence_records.append(ev24)

        # 48h Horizon Evidence Record
        ev48 = EvidenceRecordSchema(
            source="IMD",
            source_type="WEATHER_API",
            location=loc_dict,
            parameter="rainfall_48h",
            value=r48,
            unit="mm",
            observed_at=observed_at,
            forecast_issue_time=issue_time,
            forecast_valid_time=valid_48h,
            retrieved_at=now,
            status=EvidenceStatus.LIVE if r48 is not None else EvidenceStatus.UNAVAILABLE,
            quality=EvidenceQuality.HIGH if r48 is not None else EvidenceQuality.LOW,
            dataset_name="IMD Quantitative Precipitation Forecast (QPF)",
            source_url=f"{self.base_url}/forecast",
            limitations="48h accumulated NWP rainfall forecast.",
            eligibility_reason="LIVE_IMD_TELEMETRY" if r48 is not None else "MEASUREMENT_UNAVAILABLE",
        )
        evidence_records.append(ev48)

        # 72h Horizon Evidence Record
        ev72 = EvidenceRecordSchema(
            source="IMD",
            source_type="WEATHER_API",
            location=loc_dict,
            parameter="rainfall_72h",
            value=r72,
            unit="mm",
            observed_at=observed_at,
            forecast_issue_time=issue_time,
            forecast_valid_time=valid_72h,
            retrieved_at=now,
            status=EvidenceStatus.LIVE if r72 is not None else EvidenceStatus.UNAVAILABLE,
            quality=EvidenceQuality.HIGH if r72 is not None else EvidenceQuality.LOW,
            dataset_name="IMD Quantitative Precipitation Forecast (QPF)",
            source_url=f"{self.base_url}/forecast",
            limitations="72h accumulated NWP rainfall forecast.",
            eligibility_reason="LIVE_IMD_TELEMETRY" if r72 is not None else "MEASUREMENT_UNAVAILABLE",
        )
        evidence_records.append(ev72)

        return forecast, evidence_records

    def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        district: Optional[str] = None,
    ) -> Tuple[WeatherForecastData, List[EvidenceRecordSchema]]:
        """Synchronously fetch and normalize weather forecast from IMD."""
        params = {"lat": latitude, "lon": longitude}
        if district:
            params["district"] = district

        data = self.get(endpoint="/forecast", params=params)
        return self._normalize_payload(data, latitude, longitude, district)

    async def fetch_forecast_async(
        self,
        latitude: float,
        longitude: float,
        district: Optional[str] = None,
    ) -> Tuple[WeatherForecastData, List[EvidenceRecordSchema]]:
        """Asynchronously fetch and normalize weather forecast from IMD."""
        params = {"lat": latitude, "lon": longitude}
        if district:
            params["district"] = district

        data = await self.get_async(endpoint="/forecast", params=params)
        return self._normalize_payload(data, latitude, longitude, district)
