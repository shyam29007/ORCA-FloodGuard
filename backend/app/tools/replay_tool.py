"""Historical replay simulation engine tool for past flood events (e.g. July 2023 Punjab floods)."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import uuid

# Pre-compiled chronological sequence of the July 2023 Sutlej deluge
HISTORICAL_SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "2023_punjab_monsoon_floods": [
        {
            "step": 1,
            "timestamp": "2023-07-09T06:00:00Z",
            "weather_rainfall_24h": 35.0,
            "river_level_m": 213.2,
            "dam_discharge_cusecs": 30000.0,
            "risk": "MODERATE",
            "notes": "Intense rainfall begins in catchment area of Sutlej and Beas.",
        },
        {
            "step": 2,
            "timestamp": "2023-07-09T18:00:00Z",
            "weather_rainfall_24h": 85.0,
            "river_level_m": 213.8,
            "dam_discharge_cusecs": 75000.0,
            "risk": "HIGH",
            "notes": "Bhakra and Pong reservoirs see heavy inflows; emergency spillway releases initiated.",
        },
        {
            "step": 3,
            "timestamp": "2023-07-10T06:00:00Z",
            "weather_rainfall_24h": 140.0,
            "river_level_m": 214.8,
            "dam_discharge_cusecs": 120000.0,
            "risk": "CRITICAL",
            "notes": "Peak discharge passes Ropar headworks; breach reported near Gidderpindi embankment.",
        },
        {
            "step": 4,
            "timestamp": "2023-07-11T06:00:00Z",
            "weather_rainfall_24h": 65.0,
            "river_level_m": 214.4,
            "dam_discharge_cusecs": 85000.0,
            "risk": "HIGH",
            "notes": "Rain subsides but river remains swollen; relief camps active at full capacity.",
        },
    ]
}

_ACTIVE_REPLAYS: Dict[str, Dict[str, Any]] = {}


def start_replay_session(event_name: str, villages: List[str]) -> Dict[str, Any]:
    """Start a historical replay session."""
    scenario = HISTORICAL_SCENARIOS.get(event_name, HISTORICAL_SCENARIOS["2023_punjab_monsoon_floods"])
    replay_id = f"replay-{uuid.uuid4().hex[:8]}"
    _ACTIVE_REPLAYS[replay_id] = {
        "replay_id": replay_id,
        "event_name": event_name,
        "current_step": 1,
        "total_steps": len(scenario),
        "villages": villages,
        "scenario": scenario,
        "created_at": datetime.now(timezone.utc),
    }
    step_data = scenario[0]
    return {
        "replay_id": replay_id,
        "event_name": event_name,
        "current_step": 1,
        "total_steps": len(scenario),
        "simulated_timestamp": step_data["timestamp"],
        "is_completed": False,
        "village_risks": {v: step_data["risk"] for v in (villages or ["Gidderpindi", "Phillaur"])},
        "summary": step_data["notes"],
    }


def step_replay_session(replay_id: str, advance_by: int = 1) -> Dict[str, Any]:
    """Advance the replay session by one or more steps."""
    session = _ACTIVE_REPLAYS.get(replay_id)
    if not session:
        raise ValueError(f"Replay session {replay_id} not found.")

    scenario = session["scenario"]
    new_step = min(session["current_step"] + advance_by, len(scenario))
    session["current_step"] = new_step
    step_data = scenario[new_step - 1]
    is_completed = new_step >= len(scenario)

    villages = session["villages"] or ["Gidderpindi", "Phillaur"]
    return {
        "replay_id": replay_id,
        "event_name": session["event_name"],
        "current_step": new_step,
        "total_steps": len(scenario),
        "simulated_timestamp": step_data["timestamp"],
        "is_completed": is_completed,
        "village_risks": {v: step_data["risk"] for v in villages},
        "summary": step_data["notes"],
    }


def get_replay_session(replay_id: str) -> Dict[str, Any]:
    """Retrieve current status of a replay session."""
    session = _ACTIVE_REPLAYS.get(replay_id)
    if not session:
        # Fallback dummy completed session
        return {
            "replay_id": replay_id,
            "event_name": "2023_punjab_monsoon_floods",
            "current_step": 4,
            "total_steps": 4,
            "simulated_timestamp": "2023-07-11T06:00:00Z",
            "is_completed": True,
            "village_risks": {"Gidderpindi": "HIGH"},
            "summary": "Replay finished.",
        }
    scenario = session["scenario"]
    step_data = scenario[session["current_step"] - 1]
    return {
        "replay_id": replay_id,
        "event_name": session["event_name"],
        "current_step": session["current_step"],
        "total_steps": len(scenario),
        "simulated_timestamp": step_data["timestamp"],
        "is_completed": session["current_step"] >= len(scenario),
        "village_risks": {v: step_data["risk"] for v in (session["villages"] or ["Gidderpindi"])},
        "summary": step_data["notes"],
    }

