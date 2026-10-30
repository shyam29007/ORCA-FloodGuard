"""GIS query schemas and spatial parameters."""

from typing import List, Optional
from pydantic import Field
from backend.app.schemas.common import BaseSchema, Coordinates
from backend.app.schemas.evacuation import ReliefCentreSchema, EvacuationRouteSchema


class GISLocationQuery(BaseSchema):
    """Query parameters for GIS location data."""
    latitude: float
    longitude: float
    radius_km: float = 25.0


class GISLocationResponse(BaseSchema):
    """GIS location response."""
    coordinates: Coordinates
    elevation_meters: Optional[float] = None
    slope_degrees: Optional[float] = None
    is_depression_zone: bool = False
    nearby_rivers: List[str] = Field(default_factory=list)
    nearest_relief_centres: List[ReliefCentreSchema] = Field(default_factory=list)

