"""Agent 3: River Agent implementation."""

from typing import Any, Dict
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.river import RiverAgentOutput
from backend.app.tools.river_tool import find_nearest_river_station, fetch_river_reading


class RiverAgent(BaseAgent):
    """Specialist agent for river level telemetry and hydro-station monitoring."""

    def __init__(self):
        super().__init__(AgentName.RIVER)

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lat = state.get("latitude", 31.1465)
        lon = state.get("longitude", 75.1872)
        allow_simulated = state.get("include_simulated_fallback", True)

        station, dist_km = find_nearest_river_station(lat, lon)

        reading, evidence_records = fetch_river_reading(
            station_id=station.station_id,
            allow_simulated=allow_simulated,
        )

        output = RiverAgentOutput(
            nearest_station=station,
            latest_reading=reading,
            distance_to_station_km=dist_km,
            evidence_records=evidence_records,
            status="SUCCESS",
            notes=[f"Nearest CWC station {station.station_name} ({dist_km} km away). Status: {reading.status}"],
        )

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
        }
