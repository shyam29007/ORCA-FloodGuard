"""Agent 2: Weather Agent.

Retrieves 24, 48, and 72-hour rainfall forecasts, validates precipitation timestamps
and units, and returns normalized evidence records.
"""

from typing import Any, Dict
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.weather import WeatherAgentOutput
from backend.app.tools.weather_tool import fetch_weather_forecast


class WeatherAgent(BaseAgent):
    """Specialist agent for atmospheric forecasts and precipitation evidence."""

    def __init__(self):
        super().__init__(AgentName.WEATHER)

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lat = state.get("latitude", 31.1465)
        lon = state.get("longitude", 75.1872)
        district = state.get("district")
        allow_simulated = state.get("include_simulated_fallback", True)

        forecast, evidence_records = fetch_weather_forecast(
            latitude=lat,
            longitude=lon,
            district=district,
            allow_simulated=allow_simulated,
        )

        output = WeatherAgentOutput(
            forecast=forecast,
            evidence_records=evidence_records,
            status="SUCCESS",
            notes=[f"Forecast retrieved for 24h ({forecast.rainfall_24h_mm}mm), 48h ({forecast.rainfall_48h_mm}mm), 72h ({forecast.rainfall_72h_mm}mm)"],
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

