"""Master LangGraph Orchestrator assembling specialist agents into a robust workflow."""

import uuid
from typing import Dict, Any, Optional, cast
from langgraph.graph import StateGraph, START, END
from backend.app.orchestrator.state import MasterOrchestratorState
from backend.app.orchestrator.nodes import (
    validate_input_node,
    location_agent_node,
    weather_agent_node,
    river_agent_node,
    dam_agent_node,
    gis_evacuation_agent_node,
    evidence_normalization_node,
    evidence_validation_gate_node,
    deterministic_risk_assessment_node,
    alert_agent_node,
)
from backend.app.orchestrator.router import route_after_location
from backend.app.core.logging import logger

# Build LangGraph DAG
builder = StateGraph(MasterOrchestratorState)

# 1. Add Nodes
builder.add_node("validate_input", validate_input_node)
builder.add_node("location_node", location_agent_node)
builder.add_node("weather_node", weather_agent_node)
builder.add_node("river_node", river_agent_node)
builder.add_node("dam_node", dam_agent_node)
builder.add_node("gis_evacuation_node", gis_evacuation_agent_node)
builder.add_node("normalize_evidence", evidence_normalization_node)
builder.add_node("validation_gate", evidence_validation_gate_node)
builder.add_node("risk_node", deterministic_risk_assessment_node)
builder.add_node("alert_node", alert_agent_node)

# 2. Add Edges & Conditional Fan-out
builder.add_edge(START, "validate_input")
builder.add_edge("validate_input", "location_node")

# Conditional Routing from Location Agent to specialist retrieval agents
builder.add_conditional_edges(
    "location_node",
    route_after_location,
    ["weather_node", "river_node", "dam_node", "gis_evacuation_node", "alert_node"],
)

# Parallel Retrieval Fan-in to Evidence Normalization
builder.add_edge("weather_node", "normalize_evidence")
builder.add_edge("river_node", "normalize_evidence")
builder.add_edge("dam_node", "normalize_evidence")
builder.add_edge("gis_evacuation_node", "normalize_evidence")

# Normalization -> Validation Gate -> Deterministic Risk Engine -> Alert Agent -> END
builder.add_edge("normalize_evidence", "validation_gate")
builder.add_edge("validation_gate", "risk_node")
builder.add_edge("risk_node", "alert_node")
builder.add_edge("alert_node", END)

master_orchestrator = builder.compile()


def run_orchestrator(inputs: Dict[str, Any]) -> MasterOrchestratorState:
    """Execute the compiled LangGraph workflow synchronously."""
    initial_state: MasterOrchestratorState = {
        "run_id": inputs.get("run_id") or f"run-{uuid.uuid4().hex[:12]}",
        "workflow_type": inputs.get("workflow_type", "full"),
        "village_name": inputs.get("village_name"),
        "latitude": inputs.get("latitude"),
        "longitude": inputs.get("longitude"),
        "district": inputs.get("district"),
        "forecast_horizon_hours": inputs.get("forecast_horizon_hours", 72),
        "include_simulated_fallback": inputs.get("include_simulated_fallback", True),
        "operational_mode": inputs.get("operational_mode", False),
        "evidence_pool": [],
        "agent_traces": {},
        "errors": [],
    }

    logger.info("Starting Master LangGraph Orchestrator execution for run %s", initial_state["run_id"])
    final_state = master_orchestrator.invoke(initial_state)
    logger.info("Completed Master LangGraph Orchestrator execution for run %s. Risk: %s",
                final_state.get("run_id"), final_state.get("overall_risk"))
    return cast(MasterOrchestratorState, final_state)

