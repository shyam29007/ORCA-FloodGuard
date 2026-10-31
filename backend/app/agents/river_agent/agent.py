"""Agent 3: River Agent implementation."""

from typing import Any, Dict
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.river import RiverAgentOutput
from backend.app.tools.river_tool import find_nearest_river_station, fetch_river_reading


class RiverAgent(BaseAgent):
    """Specialist agent for river level telemetry and hydro-station monitoring."""

    def __init__(self):
        super().__init__(AgentName.RIVER, provider_dependency="CWC (Central Water Commission)")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lat = state.get("latitude", 31.1465)
        lon = state.get("longitude", 75.1872)
        allow_simulated = state.get("include_simulated_fallback", True)

        station, dist_km = find_nearest_river_station(lat, lon)

        reading, evidence_records = fetch_river_reading(
            station_id=station.station_id,
            allow_simulated=allow_simulated,
        )

        has_reading = reading.water_level_meters is not None
        is_sim = bool(getattr(reading, "is_simulated", False) or str(getattr(reading, "status", "")) in ("SIMULATED", "EvidenceStatus.SIMULATED")) and has_reading
        is_live = (not is_sim) and has_reading

        if is_live:
            ev_mode = "LIVE"
            freshness = "FRESH"
            diag = f"Official CWC hydro-gauge telemetry retrieved from '{station.station_name}' ({reading.water_level_meters}m)."
        elif is_sim:
            ev_mode = "SIMULATED"
            freshness = "SIMULATED_SCENARIO"
            diag = f"CWC API unconfigured; simulated hydrodynamic stage for nearest gauge '{station.station_name}' ({dist_km} km away)."
        else:
            ev_mode = "UNAVAILABLE"
            freshness = "NOT_AVAILABLE"
            diag = f"CWC telemetry unconfigured and simulation disabled for station '{station.station_name}' (Operational Mode)."

        output = RiverAgentOutput(
            nearest_station=station,
            latest_reading=reading,
            distance_to_station_km=dist_km,
            evidence_records=evidence_records,
            status="SUCCESS",
            notes=[f"Nearest CWC station {station.station_name} ({dist_km} km away). Status: {reading.status}"],
        )

        trace_meta = {
            "provider_dependency": "CWC (Central Water Commission)",
            "evidence_mode": ev_mode,
            "data_freshness": freshness,
            "input_evidence_refs": ["state.latitude", "state.longitude"],
            "output_evidence_refs": [getattr(ev, "evidence_id", f"ev-r-{i}") for i, ev in enumerate(evidence_records)],
            "is_schema_validated": True,
            "is_source_authenticated": is_live,
            "is_data_freshness_validated": is_live,
            "diagnostic_message": diag,
        }

        return {
            "river_data": {
                "station": station.model_dump(),
                "reading": reading.model_dump(),
                "distance_km": dist_km,
            },
            "evidence_records": [ev.model_dump() for ev in evidence_records],
            "river_output": output.model_dump(),
            "river_level_meters": reading.water_level_meters,
            "river_is_above_warning": reading.is_above_warning,
            "river_is_above_danger": reading.is_above_danger,
            "status": "SUCCESS",
            "_trace_meta": trace_meta,
        }
