"""GIS and spatial context endpoints."""

from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.gis import GISLocationResponse
from backend.app.schemas.common import Coordinates
from backend.app.tools.elevation_tool import fetch_elevation_profile
from backend.app.tools.relief_centre_tool import find_nearest_relief_centres

router = APIRouter(prefix="/gis", tags=["GIS"])


@router.get("/location", response_model=ApiResponse[GISLocationResponse])
def get_gis_location(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    village_name: Optional[str] = Query(None),
):
    """Retrieve digital elevation profile, low-lying depression status, and nearby relief infrastructure."""
    elev, is_low, _, _ = fetch_elevation_profile(latitude, longitude, village_name)
    relief_centres = find_nearest_relief_centres(latitude, longitude, limit=3)

    resp = GISLocationResponse(
        coordinates=Coordinates(latitude=latitude, longitude=longitude),
        elevation_meters=elev,
        slope_degrees=1.2,
        is_depression_zone=is_low,
        nearby_rivers=["Sutlej River"],
        nearest_relief_centres=relief_centres,
    )
    return ApiResponse(success=True, data=resp)

