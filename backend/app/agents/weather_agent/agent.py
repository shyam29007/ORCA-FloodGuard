"""Agent 2: Weather Agent implementation."""

from typing import Any, Dict, Optional
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.weather import WeatherAgentOutput
from backend.app.tools.weather_tool import fetch_weather_forecast


class WeatherAgent(BaseAgent):
    """Specialist agent for atmospheric forecasts and precipitation evidence."""

    def __init__(self):
        super().__init__(AgentName.WEATHER)

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lat: float = float(state.get("latitude", 31.1465) or 31.1465)
        lon: float = float(state.get("longitude", 75.1872) or 75.1872)
        district: Optional[str] = state.get("district")
        allow_simulated: bool = bool(state.get("include_simulated_fallback", True))

        forecast, evidence_records = fetch_weather_forecast(
            latitude=lat,
            longitude=lon,
            district=district,
            allow_simulated=allow_simulated,
        )

        rain_note = (
            f"Forecast retrieved for 24h ({forecast.rainfall_24h_mm}mm), 48h ({forecast.rainfall_48h_mm}mm), 72h ({forecast.rainfall_72h_mm}mm)"
            if forecast.rainfall_24h_mm is not None
            else "Rainfall forecast data UNAVAILABLE (live sensor unconfigured and simulation disabled)"
        )
        output = WeatherAgentOutput(
            forecast=forecast,
            evidence_records=evidence_records,
            status="SUCCESS",
            notes=[rain_note],
        )

        return {
            "weather_data": forecast.model_dump(),
            "evidence_records": [ev.model_dump() for ev in evidence_records],
            "weather_output": output.model_dump(),
            "rainfall_24h_mm": forecast.rainfall_24h_mm,
            "rainfall_48h_mm": forecast.rainfall_48h_mm,
            "rainfall_72h_mm": forecast.rainfall_72h_mm,
            "status": "SUCCESS",
        }
