"""Location schemas and geocoding contracts."""

from typing import Optional, List
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema, Coordinates


class VillageLocation(BaseSchema):
    """Normalized village geographic metadata."""
    village_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Standard English name of the village")
    name_pa: Optional[str] = Field(default=None, description="Punjabi Gurmukhi name")
    tehsil: Optional[str] = Field(default=None, description="Tehsil / Sub-district")
    district: str = Field(..., description="District in Punjab (e.g. Jalandhar, Firozpur, Ropar)")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation_meters: Optional[float] = Field(default=None, description="Base elevation above mean sea level")
    river_basin: Optional[str] = Field(default=None, description="Main river basin (e.g. Sutlej, Beas, Ravi)")
    nearest_river: Optional[str] = Field(default=None, description="Name of the nearest river or stream")
    distance_to_river_km: Optional[float] = Field(default=None, description="Approximate distance to river course")
    is_flood_prone: bool = Field(True, description="Historical susceptibility to monsoon flooding")


class LocationResolutionRequest(BaseSchema):
    """Request to resolve village name and optional coordinates."""
    village_name: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    district: Optional[str] = None


class LocationResolutionResponse(BaseSchema):
    """Response returned by Location Agent."""
    village: VillageLocation
    resolved_via: str = Field("DATABASE", description="DATABASE, GEOCODING_TOOL, or FALLBACK")
    confidence: float = 1.0
    warnings: List[str] = Field(default_factory=list)

