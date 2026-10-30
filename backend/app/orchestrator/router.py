"""Conditional routing and branch selection for LangGraph."""

from typing import List
from backend.app.orchestrator.state import MasterOrchestratorState


def route_after_location(state: MasterOrchestratorState) -> List[str]:
    """Determine which specialist agents to fan out to based on workflow_type."""
    workflow = state.get("workflow_type", "full")

    if workflow == "weather_only":
        return ["weather_node"]
    elif workflow == "river_only":
        return ["river_node"]
    elif workflow == "evacuation_only":
        return ["gis_evacuation_node"]
    elif workflow == "alert_only":
        return ["alert_node"]

    # Default 'full' workflow: run all 4 evidence gathering agents in parallel
    return ["weather_node", "river_node", "dam_node", "gis_evacuation_node"]


def route_after_validation(state: MasterOrchestratorState) -> str:
    """Conditional check after evidence validation gate."""
    # Both valid and invalid (insufficient evidence) proceed to deterministic risk node
    # so that the deterministic risk node can formally stamp INSUFFICIENT_EVIDENCE
    # and draft an advisory explaining the missing telemetry.
    return "risk_node"

