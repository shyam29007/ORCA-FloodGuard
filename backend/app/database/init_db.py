"""Database initialization logic."""

from sqlalchemy.orm import Session
from backend.app.database.base import Base
from backend.app.database.connection import engine, SessionLocal
from backend.app.database.models import Village, DataSource, ReliefCentre, EvacuationRoute
from backend.app.database.migration import run_database_migrations
from backend.app.core.logging import logger


def init_db() -> None:
    """Create all tables in the configured database and apply any pending schema migrations."""
    logger.info("Verifying database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Applying database migrations for schema evolution...")
    run_database_migrations(engine)
    logger.info("Database tables and schema migrations verified.")


def seed_reference_data(db: Session) -> None:
    """Populate baseline reference data for Punjab villages, relief centres, and data sources."""
    # Check if already seeded
    if db.query(Village).first():
        logger.info("Database already seeded with reference villages.")
        return

    logger.info("Seeding Punjab flood-monitoring reference data...")

    # Data Sources
    sources = [
        DataSource(code="IMD", name="India Meteorological Department", source_type="WEATHER_API", description="Precipitation forecasts and satellite radar"),
        DataSource(code="CWC", name="Central Water Commission", source_type="RIVER_GAUGE", description="River stage and discharge observation stations"),
        DataSource(code="BBMB", name="Bhakra Beas Management Board", source_type="DAM_TELEMETRY", description="Reservoir levels and spillway release telemetry"),
        DataSource(code="NASA_SRTM", name="NASA SRTM Elevation Model", source_type="GIS_ELEVATION", description="Digital elevation model 30m resolution"),
        DataSource(code="OSM", name="OpenStreetMap Evacuation Corridors", source_type="GIS_ROUTING", description="Road network and relief infrastructure"),
    ]
    db.add_all(sources)

    # Villages in Punjab prone to flooding
    villages = [
        Village(
            id="vil-gidderpindi-01",
            name="Gidderpindi",
            name_pa="ਗਿੱਦੜਪਿੰਡੀ",
            district="Jalandhar",
            tehsil="Shahkot",
            latitude=31.1465,
            longitude=75.1872,
            elevation_meters=212.0,
            river_basin="Sutlej",
            nearest_river="Sutlej River",
            distance_to_river_km=1.2,
            is_flood_prone=True,
        ),
        Village(
            id="vil-shahkot-02",
            name="Shahkot",
            name_pa="ਸ਼ਾਹਕੋਟ",
            district="Jalandhar",
            tehsil="Shahkot",
            latitude=31.0827,
            longitude=75.3377,
            elevation_meters=219.0,
            river_basin="Sutlej",
            nearest_river="Sutlej River",
            distance_to_river_km=5.5,
            is_flood_prone=True,
        ),
        Village(
            id="vil-phillaur-03",
            name="Phillaur",
            name_pa="ਫਿਲੌਰ",
            district="Jalandhar",
            tehsil="Phillaur",
            latitude=31.0267,
            longitude=75.7871,
            elevation_meters=234.0,
            river_basin="Sutlej",
            nearest_river="Sutlej River",
            distance_to_river_km=0.8,
            is_flood_prone=True,
        ),
        Village(
            id="vil-harike-04",
            name="Harike",
            name_pa="ਹਰੀਕੇ",
            district="Tarn Taran",
            tehsil="Patti",
            latitude=31.1683,
            longitude=74.9600,
            elevation_meters=210.0,
            river_basin="Sutlej-Beas Confluence",
            nearest_river="Harike Barrage",
            distance_to_river_km=0.5,
            is_flood_prone=True,
        ),
        Village(
            id="vil-anandpur-05",
            name="Anandpur Sahib",
            name_pa="ਅਨੰਦਪੁਰ ਸਾਹਿਬ",
            district="Rupnagar",
            tehsil="Anandpur Sahib",
            latitude=31.2359,
            longitude=76.4989,
            elevation_meters=298.0,
            river_basin="Sutlej",
            nearest_river="Sutlej River",
            distance_to_river_km=2.0,
            is_flood_prone=True,
        ),
        Village(
            id="vil-firozpur-06",
            name="Firozpur Rural",
            name_pa="ਫ਼ਿਰੋਜ਼ਪੁਰ ਦਿਹਾਤੀ",
            district="Firozpur",
            tehsil="Firozpur",
            latitude=30.9237,
            longitude=74.6065,
            elevation_meters=198.0,
            river_basin="Sutlej",
            nearest_river="Sutlej River",
            distance_to_river_km=2.5,
            is_flood_prone=True,
        ),
    ]
    db.add_all(villages)

    # Relief Shelters
    shelters = [
        ReliefCentre(
            id="rc-shahkot-hall",
            name="Shahkot Community Center & High School Complex",
            district="Jalandhar",
            latitude=31.0850,
            longitude=75.3410,
            elevation_meters=225.0,
            capacity_persons=1200,
            current_occupancy=0,
            contact_phone="+91-1821-220100",
            facilities_json=["Medical Post", "Potable Water Tankers", "Community Kitchen", "Power Generator"],
            is_active=True,
        ),
        ReliefCentre(
            id="rc-phillaur-civic",
            name="Phillaur Municipal Disaster Relief Shelter",
            district="Jalandhar",
            latitude=31.0350,
            longitude=75.7920,
            elevation_meters=240.0,
            capacity_persons=1000,
            current_occupancy=0,
            contact_phone="+91-1826-222300",
            facilities_json=["Emergency Ward", "Clean Drinking Water", "Food Distribution", "Child Care"],
            is_active=True,
        ),
        ReliefCentre(
            id="rc-harike-relief",
            name="Harike Govt Senior Secondary Camp",
            district="Tarn Taran",
            latitude=31.1750,
            longitude=74.9650,
            elevation_meters=218.0,
            capacity_persons=800,
            current_occupancy=0,
            contact_phone="+91-1851-245200",
            facilities_json=["First Aid", "Sanitation Blocks", "Shelter Tents"],
            is_active=True,
        ),
    ]
    db.add_all(shelters)

    # Evacuation routes
    routes = [
        EvacuationRoute(
            id="route-gidderpindi-to-shahkot",
            origin_village_id="vil-gidderpindi-01",
            destination_relief_centre_id="rc-shahkot-hall",
            route_name="NH 703 Elevated Highway Corridor",
            distance_km=16.8,
            estimated_time_minutes=25,
            verification_status="PASSABLE_WITH_CAUTION",
            elevation_profile_json={"origin_m": 212, "destination_m": 225, "lowest_m": 211},
            waypoints_json=[
                {"lat": 31.1465, "lon": 75.1872},
                {"lat": 31.1150, "lon": 75.2500},
                {"lat": 31.0850, "lon": 75.3410},
            ],
            known_hazards_json=["Minor water pooling near Lohian Khas bridge apron"],
            verification_notes="Aerial survey verified embankment elevated above 2023 peak level.",
        ),
        EvacuationRoute(
            id="route-phillaur-to-civic",
            origin_village_id="vil-phillaur-03",
            destination_relief_centre_id="rc-phillaur-civic",
            route_name="GT Road Northbound Embankment",
            distance_km=3.2,
            estimated_time_minutes=8,
            verification_status="VERIFIED_SAFE",
            elevation_profile_json={"origin_m": 234, "destination_m": 240, "lowest_m": 234},
            waypoints_json=[
                {"lat": 31.0267, "lon": 75.7871},
                {"lat": 31.0350, "lon": 75.7920},
            ],
            known_hazards_json=[],
            verification_notes="Clear high ground asphalt route, inspected by Sub-Divisional Magistrate team.",
        ),
    ]
    db.add_all(routes)

    db.commit()
    logger.info("Successfully seeded Punjab reference data.")


def run_init() -> None:
    """Entry point for initialization and seeding."""
    init_db()
    with SessionLocal() as db:
        seed_reference_data(db)


if __name__ == "__main__":
    run_init()

