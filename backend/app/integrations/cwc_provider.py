"""CWC (Central Water Commission) River Gauge and Discharge Provider Adapter."""

from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from dateutil import parser as dt_parser

from backend.app.integrations.base import BaseLiveDataProvider
from backend.app.core.config import settings
from backend.app.schemas.river import RiverStation, RiverReading
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


class CWCRiverProvider(BaseLiveDataProvider):
    """Adapter for retrieving official river gauge levels and discharge telemetry from CWC."""

    CUMECS_TO_CUSECS = 35.3146667
    service_type = "River Stage & Discharge Telemetry"
    verified_official_endpoint = "https://nwdp.nwic.gov.in/apis"
    access_restriction = (
        "Managed under National Hydrology Project (NHP); programmatic REST telemetry "
        "requires NWIC user registration and authorized API key."
    )
    requires_authentication = True
    freshness_max_hours = settings.RIVER_FRESHNESS_MAX_HOURS
    expected_credential_names = ["CWC_API_KEY", "NWIC_DATA_PORTAL_TOKEN"]
    health_check_endpoint = "/stations/CWC_SUTLEJ_PHILLAUR/reading"
    health_check_params = None
    dependent_agent_name = "River Agent"
    impact_description = "Live river gauge level and discharge evidence unavailable."
    fallback_description = "SIMULATED data, if DEMO mode is enabled; INSUFFICIENT_EVIDENCE if OPERATIONAL mode."

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        super().__init__(
            provider_name="CWC",
            base_url=base_url or settings.RIVER_API_BASE_URL,
            api_key=api_key or settings.CWC_API_KEY,
            timeout=timeout,
        )

    def _validate_health_payload(self, data: Dict[str, Any]) -> Tuple[bool, bool, Optional[str], Dict[str, Any]]:
        """Validate CWC river telemetry payload structure and determine if live measurements are present."""
        if not isinstance(data, dict):
            return False, False, None, {"error": "Expected JSON object dictionary."}

        has_level_key = any(k in data for k in ("water_level_m", "water_level_meters", "level", "discharge_cusecs", "discharge_cumecs"))
        if not has_level_key:
            return False, False, None, {"error": "Missing expected river water level or discharge fields."}

        raw_level = data.get("water_level_m")
        if raw_level is None:
            raw_level = data.get("water_level_meters")
        water_level = float(raw_level) if raw_level is not None else None

        obs_ts_str = data.get("observed_at") or data.get("timestamp")
        parsed_obs = parse_to_utc(obs_ts_str) if obs_ts_str else None

        now = datetime.now(timezone.utc)
        is_fresh = False
        if parsed_obs:
            age_hours = (now - parsed_obs).total_seconds() / 3600.0
            max_fresh = getattr(self, "freshness_max_hours", settings.RIVER_FRESHNESS_MAX_HOURS)
            is_fresh = 0 <= age_hours <= max_fresh

        has_meas = (water_level is not None)
        has_live_data = has_meas and is_fresh
        latest_ts = parsed_obs.isoformat() if parsed_obs else None

        diag = {
            "water_level_m": water_level,
            "has_measurements": has_meas,
            "observed_at": latest_ts,
            "is_fresh": is_fresh,
            "station": data.get("station_name", "Phillaur"),
        }
        return True, has_live_data, latest_ts, diag

    def _normalize_payload(
        self,
        data: Dict[str, Any],
        station: RiverStation,
    ) -> Tuple[RiverReading, List[EvidenceRecordSchema]]:
        """Normalize raw CWC payload into RiverReading and EvidenceRecordSchema."""
        now = datetime.now(timezone.utc)
        observed_at = parse_to_utc(data.get("observed_at") or data.get("timestamp"), default=now)

        # Extract water level safely; NEVER default to warning_level - 0.5 or 0.0!
        raw_level = data.get("water_level_m")
        if raw_level is None:
            raw_level = data.get("water_level_meters")
        water_level = float(raw_level) if raw_level is not None else None

        # Extract discharge rate safely (handle cumecs or cusecs)
        raw_discharge = data.get("discharge_cusecs")
        if raw_discharge is not None:
            discharge = float(raw_discharge)
        elif data.get("discharge_cumecs") is not None:
            discharge = round(float(data["discharge_cumecs"]) * self.CUMECS_TO_CUSECS, 1)
        else:
            discharge = None

        trend = str(data.get("trend") or "UNKNOWN").upper()
        if trend not in ("RISING", "FALLING", "STEADY", "UNKNOWN"):
            trend = "UNKNOWN"

        # Threshold evaluations (strictly requiring valid water_level)
        if water_level is not None:
            is_above_warning = water_level >= station.warning_level_meters
            is_above_danger = water_level >= station.danger_level_meters
            buffer_to_danger = round(station.danger_level_meters - water_level, 2)
        else:
            is_above_warning = False
            is_above_danger = False
            buffer_to_danger = None

        status = EvidenceStatus.LIVE if water_level is not None else EvidenceStatus.UNAVAILABLE

        reading = RiverReading(
            station_id=station.station_id,
            water_level_meters=water_level,
            discharge_cusecs=discharge,
            trend=trend,
            status=status,
            observed_at=observed_at,
            is_above_warning=is_above_warning,
            is_above_danger=is_above_danger,
            buffer_to_danger_meters=buffer_to_danger,
        )

        evidence_records: List[EvidenceRecordSchema] = []
        loc_dict = {
            "station_id": station.station_id,
            "station_name": station.station_name,
            "river": station.river_name,
            "district": station.district,
        }

        # River Water Level Evidence Record
        ev_level = EvidenceRecordSchema(
            source="CWC",
            source_type="RIVER_GAUGE",
            location=loc_dict,
            parameter="river_water_level",
            value=water_level,
            unit="m",
            observed_at=observed_at,
            retrieved_at=now,
            status=status,
            quality=EvidenceQuality.HIGH if water_level is not None else EvidenceQuality.LOW,
            dataset_name="CWC River Stage & Discharge Telemetry",
            source_url=f"{self.base_url}/stations/{station.station_id}/reading",
            limitations="Real-time acoustic/optical water-level transducer telemetry.",
            eligibility_reason="LIVE_CWC_TELEMETRY" if water_level is not None else "MEASUREMENT_UNAVAILABLE",
        )
        evidence_records.append(ev_level)

        # River Discharge Evidence Record (if available)
        if discharge is not None:
            ev_discharge = EvidenceRecordSchema(
                source="CWC",
                source_type="RIVER_GAUGE",
                location=loc_dict,
                parameter="river_discharge",
                value=discharge,
                unit="cusecs",
                observed_at=observed_at,
                retrieved_at=now,
                status=EvidenceStatus.LIVE,
                quality=EvidenceQuality.HIGH,
                dataset_name="CWC River Stage & Discharge Telemetry",
                source_url=f"{self.base_url}/stations/{station.station_id}/reading",
                limitations="Standard rating-curve discharge calculation approximation.",
                eligibility_reason="LIVE_CWC_TELEMETRY",
            )
            evidence_records.append(ev_discharge)

        return reading, evidence_records

    def fetch_station_reading(
        self,
        station_id: str,
        station: RiverStation,
    ) -> Tuple[RiverReading, List[EvidenceRecordSchema]]:
        """Synchronously fetch and normalize telemetry reading for a specific CWC gauge station."""
        data = self.get(endpoint=f"/stations/{station_id}/reading")
        return self._normalize_payload(data, station)

    async def fetch_station_reading_async(
        self,
        station_id: str,
        station: RiverStation,
    ) -> Tuple[RiverReading, List[EvidenceRecordSchema]]:
        """Asynchronously fetch and normalize telemetry reading for a specific CWC gauge station."""
        data = await self.get_async(endpoint=f"/stations/{station_id}/reading")
        return self._normalize_payload(data, station)
