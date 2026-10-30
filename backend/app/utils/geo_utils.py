"""Geospatial distance and coordinate calculation utilities."""

import math
from typing import Tuple


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometers."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(radius_km * c, 2)


def is_within_punjab_bounds(latitude: float, longitude: float) -> bool:
    """Check if coordinates fall within Punjab state geographic bounding box."""
    return 29.5 <= latitude <= 32.6 and 73.8 <= longitude <= 77.0

