"""Weather endpoints."""

from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.weather import WeatherForecastData
from backend.app.tools.weather_tool import fetch_weather_forecast

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/forecast", response_model=ApiResponse[WeatherForecastData])
def get_weather_forecast(
    latitude: float = Query(31.1465, ge=-90.0, le=90.0, description="Latitude"),
    longitude: float = Query(75.1872, ge=-180.0, le=180.0, description="Longitude"),
    district: Optional[str] = Query(None, description="Punjab district"),
    include_simulated: bool = Query(True, description="Allow simulated evidence fallback"),
):
    """Retrieve 24/48/72-hour precipitation forecast and atmospheric telemetry."""
    forecast, _ = fetch_weather_forecast(
        latitude=latitude,
        longitude=longitude,
        district=district,
        allow_simulated=include_simulated,
    )
    return ApiResponse(
        success=True,
        message="Forecast retrieved successfully",
        data=forecast,
    )

