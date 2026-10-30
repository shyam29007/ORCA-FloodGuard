"""Geocoding tool for Punjab villages and coordinates resolution."""

import math
from typing import Optional, Dict, Any, List
from backend.app.schemas.location import VillageLocation

# Reference Punjab flood zone villages
PUNJAB_VILLAGES_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "Gidderpindi",
        "name_pa": "ਗਿੱਦੜਪਿੰਡੀ",
        "district": "Jalandhar",
        "tehsil": "Shahkot",
        "latitude": 31.1465,
        "longitude": 75.1872,
        "elevation_meters": 212.0,
        "river_basin": "Sutlej",
        "nearest_river": "Sutlej River",
        "distance_to_river_km": 1.2,
        "is_flood_prone": True,
    },
    {
        "name": "Shahkot",
        "name_pa": "ਸ਼ਾਹਕੋਟ",
        "district": "Jalandhar",
        "tehsil": "Shahkot",
        "latitude": 31.0827,
        "longitude": 75.3377,
        "elevation_meters": 219.0,
        "river_basin": "Sutlej",
        "nearest_river": "Sutlej River",
        "distance_to_river_km": 5.5,
        "is_flood_prone": True,
    },
    {
        "name": "Phillaur",
        "name_pa": "ਫਿਲੌਰ",
        "district": "Jalandhar",
        "tehsil": "Phillaur",
        "latitude": 31.0267,
        "longitude": 75.7871,
        "elevation_meters": 234.0,
        "river_basin": "Sutlej",
        "nearest_river": "Sutlej River",
        "distance_to_river_km": 0.8,
        "is_flood_prone": True,
    },
    {
        "name": "Harike",
        "name_pa": "ਹਰੀਕੇ",
        "district": "Tarn Taran",
        "tehsil": "Patti",
        "latitude": 31.1683,
        "longitude": 74.9600,
        "elevation_meters": 210.0,
        "river_basin": "Sutlej-Beas Confluence",
        "nearest_river": "Harike Barrage",
        "distance_to_river_km": 0.5,
        "is_flood_prone": True,
    },
    {
        "name": "Anandpur Sahib",
        "name_pa": "ਅਨੰਦਪੁਰ ਸਾਹਿਬ",
        "district": "Rupnagar",
        "tehsil": "Anandpur Sahib",
        "latitude": 31.2359,
        "longitude": 76.4989,
        "elevation_meters": 298.0,
        "river_basin": "Sutlej",
        "nearest_river": "Sutlej River",
        "distance_to_river_km": 2.0,
        "is_flood_prone": True,
    },
    {
        "name": "Firozpur Rural",
        "name_pa": "ਫ਼ਿਰੋਜ਼ਪੁਰ ਦਿਹਾਤੀ",
        "district": "Firozpur",
        "tehsil": "Firozpur",
        "latitude": 30.9237,
        "longitude": 74.6065,
        "elevation_meters": 198.0,
        "river_basin": "Sutlej",
        "nearest_river": "Sutlej River",
        "distance_to_river_km": 2.5,
        "is_flood_prone": True,
    },
]


def resolve_location(
    village_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    district: Optional[str] = None,
) -> Optional[VillageLocation]:
    """Resolve location by name or coordinates against Punjab registry."""
    if village_name:
        clean_name = village_name.strip().lower()
        for item in PUNJAB_VILLAGES_CATALOG:
            if clean_name in item["name"].lower() or item["name"].lower() in clean_name:
                return VillageLocation(**item)

    if latitude is not None and longitude is not None:
        # Find nearest Punjab known village
        def dist(item):
            return math.hypot(item["latitude"] - latitude, item["longitude"] - longitude)

        nearest = min(PUNJAB_VILLAGES_CATALOG, key=dist)
        # If within ~30 km (~0.3 degrees), return with nearest contextual river
        if dist(nearest) < 0.35:
            return VillageLocation(
                name=village_name or nearest["name"],
                district=district or nearest["district"],
                latitude=latitude,
                longitude=longitude,
                elevation_meters=nearest["elevation_meters"],
                river_basin=nearest["river_basin"],
                nearest_river=nearest["nearest_river"],
                distance_to_river_km=round(dist(nearest) * 111.0, 1),
                is_flood_prone=True,
            )

        # Fallback for general Punjab coordinates
        return VillageLocation(
            name=village_name or f"Loc ({latitude:.3f}, {longitude:.3f})",
            district=district or "Punjab",
            latitude=latitude,
            longitude=longitude,
            elevation_meters=220.0,
            river_basin="Sutlej",
            nearest_river="Sutlej River",
            distance_to_river_km=5.0,
            is_flood_prone=True,
        )

    return None

