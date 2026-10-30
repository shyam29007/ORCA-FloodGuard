"""Historical replay and scenario simulation schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema


class HistoricalReplayStartRequest(BaseSchema):
    """Parameters to initiate a historical replay simulation."""
    event_name: str = Field(..., description="e.g., '2023_punjab_monsoon_floods'")
    target_villages: List[str] = Field(default_factory=list)
    start_date: Optional[str] = Field(default="2023-07-09T00:00:00Z")
    end_date: Optional[str] = Field(default="2023-07-12T00:00:00Z")
    step_size_hours: int = Field(default=6, ge=1, le=24)


class HistoricalReplayStatusResponse(BaseSchema):
    """Current state of a historical replay session."""
    replay_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str
    current_step: int
    total_steps: int
    simulated_timestamp: datetime
    is_completed: bool = False
    village_risks: Dict[str, str] = Field(default_factory=dict)
    summary: Optional[str] = None


class HistoricalReplayStepRequest(BaseSchema):
    """Advance the replay session by one or more time steps."""
    steps_to_advance: int = Field(1, ge=1, le=10)

