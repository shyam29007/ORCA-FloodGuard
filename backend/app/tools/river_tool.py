"""River gauge station and stage observation tool for Punjab river basins."""

import math
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from backend.app.core.logging import logger
from backend.app.schemas.river import RiverStation, RiverReading
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus, EvidenceQuality
from backend.app.integrations.cwc_provider import CWCRiverProvider

PUNJAB_RIVER_STATIONS: List[RiverStation] = [
    RiverStation(
        station_id="CWC_SUTLEJ_PHILLAUR",
        station_name="Phillaur Gauge Site",
        river_name="Sutlej",
        district="Jalandhar",
        latitude=31.0267,
        longitude=75.7871,
        warning_level_meters=235.0,
        danger_level_meters=236.0,
        highest_flood_level_meters=236.8,
    ),
    RiverStation(
        station_id="CWC_SUTLEJ_LOHIAN",
        station_name="Lohian Khas / Gidderpindi Railway Bridge",
        river_name="Sutlej",
        district="Jalandhar",
        latitude=31.1465,
        longitude=75.1872,
        warning_level_meters=213.5,
        danger_level_meters=214.5,
        highest_flood_level_meters=215.2,
    ),
    RiverStation(
        station_id="CWC_SUTLEJ_ROPAR",
        station_name="Ropar Headworks",
        river_name="Sutlej",
        district="Rupnagar",
        latitude=30.9700,
        longitude=76.5200,
        warning_level_meters=299.0,
        danger_level_meters=300.0,
        highest_flood_level_meters=301.2,
    ),
    RiverStation(
        station_id="CWC_HARIKE_BARRAGE",
        station_name="Harike Confluence Barrage",
        river_name="Sutlej-Beas",
        district="Tarn Taran",
        latitude=31.1683,
        longitude=74.9600,
        warning_level_meters=211.0,
        danger_level_meters=212.0,
        highest_flood_level_meters=212.9,
    ),
    RiverStation(
        station_id="CWC_SUTLEJ_HUSSAINIWALA",
        station_name="Hussainiwala Headworks",
        river_name="Sutlej",
        district="Firozpur",
        latitude=30.9237,
        longitude=74.6065,
        warning_level_meters=199.5,
        danger_level_meters=200.5,
        highest_flood_level_meters=201.4,
    ),
]


def find_nearest_river_station(latitude: float, longitude: float) -> Tuple[RiverStation, float]:
    """Find the nearest CWC monitoring station and distance in km."""
    def dist(s: RiverStation):
        return math.hypot(s.latitude - latitude, s.longitude - longitude)

    nearest = min(PUNJAB_RIVER_STATIONS, key=dist)
    dist_km = round(dist(nearest) * 111.0, 1)
    return nearest, dist_km


def fetch_river_reading(
    station_id: str,
    allow_simulated: bool = True,
) -> Tuple[RiverReading, List[EvidenceRecordSchema]]:
    """Retrieve river gauge level and discharge for a specific station."""
    now = datetime.now(timezone.utc)
    evidence_records: List[EvidenceRecordSchema] = []

    station = next((s for s in PUNJAB_RIVER_STATIONS if s.station_id == station_id), PUNJAB_RIVER_STATIONS[0])

    # 1. Attempt live API retrieval via CWCRiverProvider if configured
    provider = CWCRiverProvider()
    if provider.is_configured():
        try:
            return provider.fetch_station_reading(station_id=station_id, station=station)
        except Exception as e:
            logger.warning("CWC river provider failed: %s; falling back according to simulation configuration.", str(e))

    # 2. Fallback: Simulation or Explicit UNAVAILABLE
    current_lvl = station.warning_level_meters + 0.2 if allow_simulated else None
    status = EvidenceStatus.SIMULATED if allow_simulated else EvidenceStatus.UNAVAILABLE
    source_name = "CWC_TELEMETRY_SAMPLE" if allow_simulated else "CWC"

    reading = RiverReading(
        station_id=station_id,
        water_level_meters=current_lvl,
        discharge_cusecs=68000.0 if allow_simulated else None,
        trend="RISING" if allow_simulated else "UNKNOWN",
        status=status,
        is_simulated=(status == EvidenceStatus.SIMULATED),
        observed_at=now,
        is_above_warning=current_lvl >= station.warning_level_meters if current_lvl is not None else False,
        is_above_danger=current_lvl >= station.danger_level_meters if current_lvl is not None else False,
        buffer_to_danger_meters=round(station.danger_level_meters - current_lvl, 2) if current_lvl is not None else None,
    )

    ev = EvidenceRecordSchema(
        source=source_name,
        source_type="RIVER_GAUGE",
        location={"station_id": station_id, "name": station.station_name, "river": station.river_name},
        parameter="river_water_level",
        value=current_lvl,
        unit="m",
        observed_at=now,
        retrieved_at=now,
        status=status,
        quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
        dataset_name="CWC River Gauge Network",
        limitations="Simulated river stage reading based on 2023 monsoon crest scenarios." if allow_simulated else "Live river telemetry feed is unconfigured or unavailable.",
        eligibility_reason="SIMULATION_DEMO" if allow_simulated else "MEASUREMENT_UNAVAILABLE",
    )
    evidence_records.append(ev)

    return reading, evidence_records
