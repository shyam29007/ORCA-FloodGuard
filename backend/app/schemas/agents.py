"""Agent metadata and execution trace contracts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field
import uuid
from backend.app.schemas.common import BaseSchema


class AgentName(str, Enum):
    """Names of the specialist agents and orchestrator."""
    LOCATION = "location_agent"
    WEATHER = "weather_agent"
    RIVER = "river_agent"
    DAM = "dam_agent"
    GIS_EVACUATION = "gis_evacuation_agent"
    ALERT = "alert_agent"
    ORCHESTRATOR = "master_orchestrator"


class AgentExecutionStatus(str, Enum):
    """Lifecycle status of an agent invocation."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AgentExecutionTrace(BaseSchema):
    """Detailed audit trace for a specialist agent execution."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    assessment_id: Optional[str] = None
    agent_name: AgentName
    status: AgentExecutionStatus = AgentExecutionStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class OrchestratorRunStatus(BaseSchema):
    """High-level summary of a complete orchestrator execution."""
    run_id: str
    status: str  # RUNNING, COMPLETED, FAILED
    started_at: datetime
    completed_at: Optional[datetime] = None
    agent_traces: Dict[str, AgentExecutionTrace] = Field(default_factory=dict)
    errors: Dict[str, str] = Field(default_factory=dict)

