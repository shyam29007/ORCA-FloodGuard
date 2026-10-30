"""API routes module exports."""

from backend.app.api.routes import (
    health,
    flood,
    agents,
    weather,
    river,
    dam,
    gis,
    evacuation,
    replay,
    reports,
    alerts,
)

__all__ = [
    "health",
    "flood",
    "agents",
    "weather",
    "river",
    "dam",
    "gis",
    "evacuation",
    "replay",
    "reports",
    "alerts",
]

