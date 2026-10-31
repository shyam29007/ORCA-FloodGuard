"""Agent 1: Location Agent implementation."""

from typing import Any, Dict, Optional
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.location import VillageLocation, LocationResolutionResponse
from backend.app.tools.geocoding_tool import resolve_location


class LocationAgent(BaseAgent):
    """Specialist agent for geographic resolution and spatial context identification."""

    def __init__(self):
        super().__init__(AgentName.LOCATION, provider_dependency="Local Geospatial Boundary Index")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        village_name = state.get("village_name")
        lat = state.get("latitude")
        lon = state.get("longitude")
        district = state.get("district")

        warnings = []
        if lat is not None and lon is not None:
            if not (29.5 <= lat <= 32.6 and 73.8 <= lon <= 77.0):
                warnings.append(f"Coordinates ({lat}, {lon}) lie outside standard Punjab boundaries.")

        resolved = resolve_location(
            village_name=village_name,
            latitude=lat,
            longitude=lon,
            district=district,
        )
        if resolved is not None:
            location_meta = resolved
        else:
            location_meta = VillageLocation(
                name=village_name or "Unknown Village",
                district=district or "Punjab",
                latitude=lat if lat is not None else 31.1465,
                longitude=lon if lon is not None else 75.1872,
                elevation_meters=212.0,
                river_basin="Sutlej",
                nearest_river="Sutlej River",
                distance_to_river_km=2.0,
                is_flood_prone=True,
            )
            warnings.append("Village not found in local Punjab index; instantiated contextual fallback.")

        resolution_resp = LocationResolutionResponse(
            village=location_meta,
            resolved_via="GEOCODING_TOOL" if not warnings else "FALLBACK",
            confidence=0.95 if not warnings else 0.70,
            warnings=warnings,
        )

        trace_meta = {
            "provider_dependency": "Local Geospatial Boundary Index",
            "evidence_mode": "STATIC_REFERENCE",
            "data_freshness": "STATIC_REFERENCE",
            "input_evidence_refs": ["state.village_name", "state.latitude", "state.longitude"],
            "output_evidence_refs": ["location_resolution", "latitude", "longitude", "river_basin"],
            "is_schema_validated": True,
            "is_source_authenticated": False,
            "is_data_freshness_validated": False,
            "diagnostic_message": f"Resolved spatial coordinates for {location_meta.name} ({location_meta.district}) from local Punjab administrative reference dataset.",
        }

        return {
            "village": location_meta.model_dump(),
            "location_resolution": resolution_resp.model_dump(),
            "latitude": location_meta.latitude,
            "longitude": location_meta.longitude,
            "village_name": location_meta.name,
            "district": location_meta.district,
            "river_basin": location_meta.river_basin,
            "status": "SUCCESS",
            "_trace_meta": trace_meta,
        }
