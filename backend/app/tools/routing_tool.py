"""Evacuation route generation and road segment safety verification tool."""

from datetime import datetime, timezone
from typing import List, Optional
from backend.app.schemas.evacuation import (
    EvacuationRouteSchema,
    RouteVerificationStatus,
    RouteInspectionEvidence,
    ReliefCentreSchema,
)


def generate_candidate_routes(
    origin_village_id: str,
    village_name: str,
    origin_lat: float,
    origin_lon: float,
    relief_centres: List[ReliefCentreSchema],
    inspection_records: Optional[List[RouteInspectionEvidence]] = None,
) -> List[EvacuationRouteSchema]:
    """Generate candidate evacuation routes with strict verification status.

    Safety Rule: Never infer route safety from shortest distance, elevation, or road availability alone.
    A route can ONLY be marked VERIFIED_OPEN if a valid, authorized field inspection is attached.
    """
    routes: List[EvacuationRouteSchema] = []
    inspections_by_route = {insp.route_id: insp for insp in (inspection_records or [])}

    for rc in relief_centres:
        route_id = f"route-{origin_village_id[:8]}-to-{rc.relief_centre_id[:8]}"
        dist_km = rc.distance_km or 10.0
        time_mins = max(5, int((dist_km / 35.0) * 60))

        # Check if an authorized inspection exists for this route
        inspection = inspections_by_route.get(route_id)
        if inspection and inspection.current_status == RouteVerificationStatus.VERIFIED_OPEN:
            status = RouteVerificationStatus.VERIFIED_OPEN
            notes = f"Verified by {inspection.authorized_source} at {inspection.inspection_timestamp.isoformat()}."
            hazards = []
        elif inspection and inspection.current_status == RouteVerificationStatus.REPORTED_BLOCKED:
            status = RouteVerificationStatus.REPORTED_BLOCKED
            notes = f"Reported blocked by {inspection.authorized_source}."
            hazards = inspection.supporting_evidence
        else:
            # Default to CANDIDATE / UNVERIFIED. Never mark VERIFIED_OPEN without inspection!
            status = RouteVerificationStatus.CANDIDATE
            notes = "Candidate route generated from road network topology. Field safety verification pending."
            hazards = ["Unverified road corridor; ground emergency crews must assess water depth before transit."]

        r = EvacuationRouteSchema(
            route_id=route_id,
            origin_village_id=origin_village_id,
            destination_relief_centre_id=rc.relief_centre_id,
            route_name=f"Corridor from {village_name} to {rc.name}",
            distance_km=dist_km,
            estimated_time_minutes=time_mins,
            verification_status=status,
            elevation_profile={"origin_lat": origin_lat, "destination_elevation_m": rc.elevation_meters},
            known_hazards=hazards,
            waypoints=[
                {"lat": origin_lat, "lon": origin_lon},
                {"lat": (origin_lat + rc.latitude) / 2.0, "lon": (origin_lon + rc.longitude) / 2.0},
                {"lat": rc.latitude, "lon": rc.longitude},
            ],
            verification_notes=notes,
            inspection=inspection,
        )
        routes.append(r)

    return routes
