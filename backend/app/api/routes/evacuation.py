"""Evacuation route planning and relief shelter endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.evacuation import EvacuationRouteSchema, ReliefCentreSchema
from backend.app.services.evacuation_service import EvacuationService
from backend.app.tools.routing_tool import generate_candidate_routes
from backend.app.tools.relief_centre_tool import find_nearest_relief_centres

router = APIRouter(prefix="/evacuation", tags=["Evacuation"])


@router.get("/routes", response_model=ApiResponse[List[EvacuationRouteSchema]])
def get_evacuation_routes(
    village_id: Optional[str] = Query(None, description="Village UUID"),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    village_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve designated evacuation routes linking the village to safety shelters."""
    service = EvacuationService(db)
    if village_id:
        routes = service.get_village_routes(village_id)
        if routes:
            return ApiResponse(success=True, data=routes)

    lat = latitude or 31.1465
    lon = longitude or 75.1872
    centres = find_nearest_relief_centres(lat, lon, limit=3)
    generated = generate_candidate_routes(
        origin_village_id=village_id or "vil-generic",
        village_name=village_name or "Village",
        origin_lat=lat,
        origin_lon=lon,
        relief_centres=centres,
    )
    return ApiResponse(success=True, data=generated)


@router.get("/relief-centres", response_model=ApiResponse[List[ReliefCentreSchema]])
def get_relief_centres(
    district: Optional[str] = Query(None, description="Filter by Punjab district"),
    db: Session = Depends(get_db),
):
    """List operational disaster relief centres and camps."""
    service = EvacuationService(db)
    centres = service.get_relief_centres(district=district)
    return ApiResponse(success=True, data=centres)

