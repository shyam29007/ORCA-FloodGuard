"""Evacuation planning and shelter management service."""

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.repositories import ReliefCentreRepository, EvacuationRouteRepository
from backend.app.database.models import ReliefCentre, EvacuationRoute
from backend.app.tools.relief_centre_tool import find_nearest_relief_centres
from backend.app.schemas.evacuation import ReliefCentreSchema, EvacuationRouteSchema, RouteVerificationStatus


class EvacuationService:
    def __init__(self, db: Session):
        self.db = db
        self.rc_repo = ReliefCentreRepository(db)
        self.route_repo = EvacuationRouteRepository(db)

    def get_relief_centres(self, district: Optional[str] = None) -> List[ReliefCentreSchema]:
        db_centres = self.rc_repo.get_all(district=district)
        if db_centres:
            return [
                ReliefCentreSchema(
                    relief_centre_id=c.id,
                    name=c.name,
                    district=c.district,
                    latitude=c.latitude,
                    longitude=c.longitude,
                    elevation_meters=c.elevation_meters,
                    capacity_persons=c.capacity_persons,
                    current_occupancy=None,
                    available_capacity=None,
                    is_live_verified=False,
                    verification_status="REGISTERED_REFERENCE",
                    contact_phone=c.contact_phone,
                    facilities=c.facilities_json or [],
                    is_active=c.is_active,
                )
                for c in db_centres
            ]
        # Fallback to in-memory catalog
        return find_nearest_relief_centres(31.1, 75.2, district=district, limit=10)

    def get_village_routes(self, village_id: str) -> List[EvacuationRouteSchema]:
        db_routes = self.route_repo.get_routes_for_village(village_id)
        return [
            EvacuationRouteSchema(
                route_id=r.id,
                origin_village_id=r.origin_village_id,
                destination_relief_centre_id=r.destination_relief_centre_id,
                route_name=r.route_name,
                distance_km=r.distance_km,
                estimated_time_minutes=r.estimated_time_minutes,
                verification_status=RouteVerificationStatus(r.verification_status),
                elevation_profile=r.elevation_profile_json or {},
                known_hazards=r.known_hazards_json or [],
                waypoints=r.waypoints_json or [],
                verification_notes=r.verification_notes,
            )
            for r in db_routes
        ]

