"""Historical flood replay simulation endpoints."""

from fastapi import APIRouter
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.replay import (
    HistoricalReplayStartRequest,
    HistoricalReplayStatusResponse,
    HistoricalReplayStepRequest,
)
from backend.app.services.replay_service import ReplayService

router = APIRouter(prefix="/replay", tags=["Historical Replay"])


@router.post("/start", response_model=ApiResponse[HistoricalReplayStatusResponse])
def start_replay(req: HistoricalReplayStartRequest):
    """Initiate a time-stepped simulation session of a past major flood event."""
    resp = ReplayService.start_replay(req)
    return ApiResponse(
        success=True,
        message=f"Replay '{req.event_name}' started",
        data=resp,
    )


@router.get("/{replay_id}", response_model=ApiResponse[HistoricalReplayStatusResponse])
def get_replay_status(replay_id: str):
    """Retrieve current timestamp, step index, and village risk statuses for an active replay."""
    resp = ReplayService.get_status(replay_id)
    return ApiResponse(success=True, data=resp)


@router.post("/{replay_id}/step", response_model=ApiResponse[HistoricalReplayStatusResponse])
def advance_replay_step(replay_id: str, req: HistoricalReplayStepRequest):
    """Step forward through the disaster timeline by one or more chronological intervals."""
    resp = ReplayService.step_replay(replay_id, req)
    return ApiResponse(
        success=True,
        message=f"Replay advanced to step {resp.current_step}/{resp.total_steps}",
        data=resp,
    )

