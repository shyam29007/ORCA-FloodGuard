"""River gauge station and reading endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.river import RiverStation, RiverReading
from backend.app.tools.river_tool import PUNJAB_RIVER_STATIONS, fetch_river_reading

router = APIRouter(prefix="/river", tags=["River"])


@router.get("/stations", response_model=ApiResponse[List[RiverStation]])
def get_river_stations():
    """List all CWC river gauge observation stations in Punjab."""
    return ApiResponse(
        success=True,
        data=PUNJAB_RIVER_STATIONS,
    )


@router.get("/readings/{station_id}", response_model=ApiResponse[RiverReading])
def get_station_reading(station_id: str):
    """Retrieve the latest telemetry reading for a specified river gauge station."""
    station = next((s for s in PUNJAB_RIVER_STATIONS if s.station_id == station_id), None)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found.",
        )
    reading, _ = fetch_river_reading(station_id, allow_simulated=True)
    return ApiResponse(success=True, data=reading)


@router.get("/status/{station_id}", response_model=ApiResponse[Dict[str, Any]])
def get_station_status(station_id: str):
    """Check warning, danger, and buffer status for a specified river gauge."""
    station = next((s for s in PUNJAB_RIVER_STATIONS if s.station_id == station_id), None)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found.",
        )
    reading, _ = fetch_river_reading(station_id, allow_simulated=True)
    return ApiResponse(
        success=True,
        data={
            "station_id": station.station_id,
            "station_name": station.station_name,
            "river": station.river_name,
            "current_water_level_m": reading.water_level_meters,
            "warning_level_m": station.warning_level_meters,
            "danger_level_m": station.danger_level_meters,
            "is_above_warning": reading.is_above_warning,
            "is_above_danger": reading.is_above_danger,
            "buffer_to_danger_m": reading.buffer_to_danger_meters,
            "trend": reading.trend,
        },
    )

