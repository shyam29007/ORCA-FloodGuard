"""Historical replay session management service."""

from typing import Dict, Any, List, Optional
from backend.app.schemas.replay import (
    HistoricalReplayStartRequest,
    HistoricalReplayStatusResponse,
    HistoricalReplayStepRequest,
)
from backend.app.tools.replay_tool import (
    start_replay_session,
    step_replay_session,
    get_replay_session,
)


class ReplayService:
    @staticmethod
    def start_replay(req: HistoricalReplayStartRequest) -> HistoricalReplayStatusResponse:
        data = start_replay_session(req.event_name, req.target_villages)
        return HistoricalReplayStatusResponse(**data)

    @staticmethod
    def step_replay(replay_id: str, req: HistoricalReplayStepRequest) -> HistoricalReplayStatusResponse:
        data = step_replay_session(replay_id, advance_by=req.steps_to_advance)
        return HistoricalReplayStatusResponse(**data)

    @staticmethod
    def get_status(replay_id: str) -> HistoricalReplayStatusResponse:
        data = get_replay_session(replay_id)
        return HistoricalReplayStatusResponse(**data)

