"""Relief shelter infrastructure tool."""

import math
from typing import List, Optional
from backend.app.schemas.evacuation import ReliefCentreSchema

PUNJAB_RELIEF_CENTRES: List[ReliefCentreSchema] = [
    ReliefCentreSchema(
        relief_centre_id="rc-shahkot-hall",
        name="Shahkot Community Center & High School Complex",
        district="Jalandhar",
        latitude=31.0850,
        longitude=75.3410,
        elevation_meters=225.0,
        capacity_persons=1200,
        current_occupancy=None,
        available_capacity=None,
        is_live_verified=False,
        verification_status="REGISTERED_REFERENCE",
        contact_phone="+91-1821-220100",
        facilities=["Medical Post", "Potable Water Tankers", "Community Kitchen", "Power Generator"],
        is_active=True,
    ),
    ReliefCentreSchema(
        relief_centre_id="rc-phillaur-civic",
        name="Phillaur Municipal Disaster Relief Shelter",
        district="Jalandhar",
        latitude=31.0350,
        longitude=75.7920,
        elevation_meters=240.0,
        capacity_persons=1000,
        current_occupancy=None,
        available_capacity=None,
        is_live_verified=False,
        verification_status="REGISTERED_REFERENCE",
        contact_phone="+91-1826-222300",
        facilities=["Emergency Ward", "Clean Drinking Water", "Food Distribution", "Child Care"],
        is_active=True,
    ),
    ReliefCentreSchema(
        relief_centre_id="rc-harike-relief",
        name="Harike Govt Senior Secondary Camp",
        district="Tarn Taran",
        latitude=31.1750,
        longitude=74.9650,
        elevation_meters=218.0,
        capacity_persons=800,
        current_occupancy=None,
        available_capacity=None,
        is_live_verified=False,
        verification_status="REGISTERED_REFERENCE",
        contact_phone="+91-1851-245200",
        facilities=["First Aid", "Sanitation Blocks", "Shelter Tents"],
        is_active=True,
    ),
]


def find_nearest_relief_centres(
    latitude: float,
    longitude: float,
    district: Optional[str] = None,
    limit: int = 3,
) -> List[ReliefCentreSchema]:
    """Find the closest active relief centres ordered by distance."""
    centres_with_dist = []
    for c in PUNJAB_RELIEF_CENTRES:
        dist_km = round(math.hypot(c.latitude - latitude, c.longitude - longitude) * 111.0, 1)
        c_copy = c.model_copy()
        c_copy.distance_km = dist_km
        centres_with_dist.append((dist_km, c_copy))

    centres_with_dist.sort(key=lambda x: x[0])
    return [c for _, c in centres_with_dist[:limit]]

