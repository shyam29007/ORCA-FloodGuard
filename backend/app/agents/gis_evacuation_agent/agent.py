"""Agent 5: GIS & Evacuation Agent implementation."""

from typing import Any, Dict
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.evacuation import GISEvacuationAgentOutput
from backend.app.tools.elevation_tool import fetch_elevation_profile
from backend.app.tools.relief_centre_tool import find_nearest_relief_centres
from backend.app.tools.routing_tool import generate_candidate_routes


class GISEvacuationAgent(BaseAgent):
    """Specialist agent for spatial topography, shelter inventory, and evacuation corridor planning."""

    def __init__(self):
        super().__init__(AgentName.GIS_EVACUATION, provider_dependency="NASA SRTM 30m DEM & OpenStreetMap")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lat = state.get("latitude", 31.1465)
        lon = state.get("longitude", 75.1872)
        village_name = state.get("village_name", "Village")
        district = state.get("district")
        village = state.get("village") or {}
        village_id = village.get("village_id", f"vil-{lat:.2f}-{lon:.2f}")
        registered_elevation = village.get("elevation_meters")

        # 1. Elevation and vertical-datum discrepancy check
        elev, is_low, elev_ev, discrepancy_warning = fetch_elevation_profile(
            latitude=lat,
            longitude=lon,
            village_name=village_name,
            registered_elevation=registered_elevation,
        )

        # 2. Nearest relief shelters
        relief_centres = find_nearest_relief_centres(lat, lon, district, limit=3)

        # 3. Candidate evacuation routes (strict verification tags: CANDIDATE / UNVERIFIED)
        routes = generate_candidate_routes(
            origin_village_id=village_id,
            village_name=village_name,
            origin_lat=lat,
            origin_lon=lon,
            relief_centres=relief_centres,
        )

        notes = [
            f"Ground elevation: {elev}m AMSL (EGM96). {len(routes)} candidate corridors generated.",
        ]
        if discrepancy_warning:
            notes.append(discrepancy_warning)

        output = GISEvacuationAgentOutput(
            village_elevation_meters=elev,
            elevation_discrepancy_warning=discrepancy_warning,
            is_low_lying_zone=is_low,
            nearest_relief_centres=relief_centres,
            evacuation_routes=routes,
            evidence_records=elev_ev,
            status="SUCCESS",
            notes=notes,
        )

        trace_meta = {
            "provider_dependency": "NASA SRTM 30m DEM & OpenStreetMap",
            "evidence_mode": "STATIC_REFERENCE",
            "data_freshness": "STATIC_REFERENCE",
            "input_evidence_refs": ["state.latitude", "state.longitude", "state.village_id"],
            "output_evidence_refs": [getattr(ev, "evidence_id", f"ev-gis-{i}") for i, ev in enumerate(elev_ev)],
            "is_schema_validated": True,
            "is_source_authenticated": False,
            "is_data_freshness_validated": False,
            "diagnostic_message": f"Elevation derived from NASA SRTM 30m DEM ({elev}m AMSL EGM96) and candidate corridors mapped via OpenStreetMap.",
        }

        res = {
            "gis_evacuation_data": {
                "elevation_meters": elev,
                "is_low_lying": is_low,
                "relief_centres": [rc.model_dump() for rc in relief_centres],
                "evacuation_routes": [rt.model_dump() for rt in routes],
            },
            "evidence_records": [ev.model_dump() for ev in elev_ev],
            "gis_evacuation_output": output.model_dump(),
            "village_elevation_meters": elev,
            "is_low_lying_zone": is_low,
            "status": "SUCCESS",
            "_trace_meta": trace_meta,
        }
        if discrepancy_warning:
            res["warnings"] = [discrepancy_warning]
        return res
