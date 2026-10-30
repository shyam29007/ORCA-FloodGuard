"""Village domain service."""

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.models import Village
from backend.app.database.repositories import VillageRepository
from backend.app.schemas.location import VillageLocation


class VillageService:
    def __init__(self, db: Session):
        self.repo = VillageRepository(db)

    def get_village(self, village_id: str) -> Optional[Village]:
        return self.repo.get_by_id(village_id)

    def find_by_name(self, name: str) -> Optional[Village]:
        return self.repo.get_by_name(name)

    def list_villages(self, limit: int = 100) -> List[Village]:
        return self.repo.get_all(limit=limit)

    def resolve_or_create(self, location_meta: VillageLocation) -> Village:
        existing = self.repo.get_by_name(location_meta.name)
        if existing:
            return existing

        village = Village(
            id=location_meta.village_id,
            name=location_meta.name,
            name_pa=location_meta.name_pa,
            district=location_meta.district,
            tehsil=location_meta.tehsil,
            latitude=location_meta.latitude,
            longitude=location_meta.longitude,
            elevation_meters=location_meta.elevation_meters,
            river_basin=location_meta.river_basin,
            nearest_river=location_meta.nearest_river,
            distance_to_river_km=location_meta.distance_to_river_km,
            is_flood_prone=location_meta.is_flood_prone,
        )
        return self.repo.create(village)

