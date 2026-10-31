"""BBMB (Bhakra Beas Management Board) Reservoir and Spillway Discharge Provider Adapter."""

from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from dateutil import parser as dt_parser

from backend.app.integrations.base import BaseLiveDataProvider
from backend.app.core.config import settings
from backend.app.schemas.dam import DamInformation
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


class BBMBDamProvider(BaseLiveDataProvider):
    """Adapter for retrieving official reservoir storage levels and spillway discharge from BBMB."""

    FEET_TO_METERS = 0.3048
    service_type = "Reservoir Storage & Spillway Discharge Telemetry"
    verified_official_endpoint = "https://bbmb.gov.in/ and https://nwdp.nwic.gov.in/"
    access_restriction = (
        "Official bulletins published via HTML/PDF; programmatic telemetry feeds "
        "federated via NWIC under Bhakra Beas Management Board, Chandigarh with institutional clearance."
    )
    requires_authentication = True
    freshness_max_hours = settings.DAM_FRESHNESS_MAX_HOURS
    expected_credential_names = ["BBMB_API_KEY", "NWIC_FEDERATED_KEY"]
    health_check_endpoint = "/telemetry"
    health_check_params = {"basin": "Sutlej"}
    dependent_agent_name = "Dam Agent"
    impact_description = "Live reservoir storage and spillway discharge evidence unavailable."
    fallback_description = "SIMULATED data, if DEMO mode is enabled; INSUFFICIENT_EVIDENCE if OPERATIONAL mode."

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        super().__init__(
            provider_name="BBMB",
            base_url=base_url or settings.DAM_API_BASE_URL,
            api_key=api_key or settings.BBMB_API_KEY,
            timeout=timeout,
        )

    def _validate_health_payload(self, data: Dict[str, Any]) -> Tuple[bool, bool, Optional[str], Dict[str, Any]]:
        """Validate BBMB dam telemetry payload structure and determine if live measurements are present."""
        if not isinstance(data, dict):
            return False, False, None, {"error": "Expected JSON object dictionary."}

        dams = data.get("dams")
        if not isinstance(dams, list):
            return False, False, None, {"error": "Missing 'dams' list in reservoir payload."}

        now = datetime.now(timezone.utc)
        has_live_dam = False
        latest_ts = None

        for dam in dams:
            outflow = dam.get("outflow_discharge_cusecs") or dam.get("discharge_cusecs")
            level_m = dam.get("water_level_m") or dam.get("water_level_ft")
            obs_str = dam.get("observed_at") or dam.get("last_updated") or data.get("timestamp")
            parsed_obs = parse_to_utc(obs_str) if obs_str else None

            if parsed_obs:
                latest_ts = parsed_obs.isoformat()
                age_hours = (now - parsed_obs).total_seconds() / 3600.0
                max_fresh = getattr(self, "freshness_max_hours", settings.DAM_FRESHNESS_MAX_HOURS)
                if 0 <= age_hours <= max_fresh:
                    if outflow is not None or level_m is not None:
                        has_live_dam = True
                        break

        any_measurements = any(
            (
                dam.get("outflow_discharge_cusecs") is not None
                or dam.get("discharge_cusecs") is not None
                or dam.get("water_level_m") is not None
                or dam.get("water_level_ft") is not None
            )
            for dam in dams
        ) if dams else False

        diag = {
            "dams_count": len(dams),
            "latest_observed_at": latest_ts,
            "has_measurements": any_measurements,
            "has_live_measurements": has_live_dam,
            "is_fresh": has_live_dam,
        }
        return True, has_live_dam, latest_ts, diag

    def _normalize_payload(
        self,
        data: Dict[str, Any],
        river_basin: Optional[str] = None,
    ) -> Tuple[List[DamInformation], List[EvidenceRecordSchema]]:
        """Normalize raw BBMB / NWIC reservoir payload into DamInformation list and EvidenceRecordSchema list."""
        now = datetime.now(timezone.utc)
        dams_list = data.get("dams") or []
        records: List[DamInformation] = []
        evidence_records: List[EvidenceRecordSchema] = []

        for item in dams_list:
            river = str(item.get("river") or "Sutlej")
            # Filter by river basin if provided
            if river_basin and river_basin.lower() not in river.lower() and river.lower() not in river_basin.lower():
                continue

            dam_id = str(item.get("dam_id") or "DAM_UNKNOWN")
            dam_name = str(item.get("name") or item.get("dam_name") or "Unknown Dam")

            # Parse water level (handle feet vs meters)
            raw_m = item.get("water_level_m") or item.get("current_water_level_meters")
            raw_ft = item.get("water_level_ft")
            if raw_m is not None:
                water_level_m = float(raw_m)
            elif raw_ft is not None:
                water_level_m = round(float(raw_ft) * self.FEET_TO_METERS, 2)
            else:
                water_level_m = None

            raw_frl = item.get("full_reservoir_level_m") or item.get("full_reservoir_level_meters")
            if raw_frl is not None:
                frl_m = float(raw_frl)
            elif item.get("full_reservoir_level_ft") is not None:
                frl_m = round(float(item["full_reservoir_level_ft"]) * self.FEET_TO_METERS, 2)
            else:
                frl_m = 500.0  # reference nominal

            # Outflow discharge (NEVER default to 30,000!)
            raw_outflow = item.get("outflow_discharge_cusecs") or item.get("discharge_cusecs")
            outflow = float(raw_outflow) if raw_outflow is not None else None

            # Inflow
            raw_inflow = item.get("inflow_cusecs")
            inflow = float(raw_inflow) if raw_inflow is not None else None

            # Capacity
            raw_cap = item.get("capacity_pct") or item.get("capacity_percent")
            capacity_pct = float(raw_cap) if raw_cap is not None else None

            gates = int(item.get("spillway_gates_open") or item.get("spillway_gates") or 0)
            obs_time = parse_to_utc(item.get("observed_at") or item.get("last_updated") or data.get("timestamp"), default=now)

            is_high = (outflow >= settings.DAM_HIGH_DISCHARGE_CUSECS) if outflow is not None else False
            is_critical = (outflow >= settings.DAM_CRITICAL_DISCHARGE_CUSECS) if outflow is not None else False
            status = EvidenceStatus.LIVE if outflow is not None else EvidenceStatus.UNAVAILABLE

            dam_info = DamInformation(
                dam_id=dam_id,
                name=dam_name,
                river=river,
                full_reservoir_level_meters=frl_m,
                current_water_level_meters=water_level_m if water_level_m is not None else 0.0,
                capacity_percent=capacity_pct if capacity_pct is not None else 0.0,
                inflow_cusecs=inflow if inflow is not None else 0.0,
                outflow_discharge_cusecs=outflow,
                spillway_gates_open=gates,
                status=status,
                last_updated=obs_time,
                is_high_discharge=is_high,
                is_critical_discharge=is_critical,
            )
            records.append(dam_info)

            loc_dict = {"dam_id": dam_id, "dam_name": dam_name, "river": river}

            # Outflow Evidence Record
            ev_outflow = EvidenceRecordSchema(
                source="BBMB",
                source_type="DAM_TELEMETRY",
                location=loc_dict,
                parameter="dam_spillway_outflow",
                value=outflow,
                unit="cusecs",
                observed_at=obs_time,
                retrieved_at=now,
                status=status,
                quality=EvidenceQuality.HIGH if outflow is not None else EvidenceQuality.LOW,
                dataset_name="BBMB Reservoir Dispatch Telemetry",
                source_url=f"{self.base_url}/telemetry",
                limitations="Automated SCADA telemetry from reservoir control gate.",
                eligibility_reason="LIVE_BBMB_TELEMETRY" if outflow is not None else "MEASUREMENT_UNAVAILABLE",
            )
            evidence_records.append(ev_outflow)

        return records, evidence_records

    def fetch_dam_telemetry(
        self,
        river_basin: Optional[str] = "Sutlej",
    ) -> Tuple[List[DamInformation], List[EvidenceRecordSchema]]:
        """Synchronously fetch and normalize dam telemetry from BBMB."""
        data = self.get(endpoint="/telemetry", params={"basin": river_basin} if river_basin else None)
        return self._normalize_payload(data, river_basin=river_basin)

    async def fetch_dam_telemetry_async(
        self,
        river_basin: Optional[str] = "Sutlej",
    ) -> Tuple[List[DamInformation], List[EvidenceRecordSchema]]:
        """Asynchronously fetch and normalize dam telemetry from BBMB."""
        data = await self.get_async(endpoint="/telemetry", params={"basin": river_basin} if river_basin else None)
        return self._normalize_payload(data, river_basin=river_basin)
