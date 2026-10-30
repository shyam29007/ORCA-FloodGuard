"""Typed shared state for LangGraph Master Orchestrator."""

from typing import TypedDict, Annotated, Optional, Dict, Any, List
from backend.app.orchestrator.reducers import (
    add_evidence_reducer,
    update_traces_reducer,
    add_errors_reducer,
)


class MasterOrchestratorState(TypedDict, total=False):
    """Shared TypedDict state passed through all graph nodes."""

    # Workflow metadata
    run_id: str
    workflow_type: str  # 'full', 'weather_only', 'river_only', 'evacuation_only', 'alert_only'
    forecast_horizon_hours: int
    include_simulated_fallback: bool
    operational_mode: bool

    # Input requests
    village_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    district: Optional[str]

    # Resolved geographic metadata
    village: Optional[Dict[str, Any]]
    location_resolution: Optional[Dict[str, Any]]
    river_basin: Optional[str]

    # Parallel specialist agent outputs
    weather_data: Optional[Dict[str, Any]]
    rainfall_24h_mm: Optional[float]
    rainfall_48h_mm: Optional[float]
    rainfall_72h_mm: Optional[float]

    river_data: Optional[Dict[str, Any]]
    river_level_meters: Optional[float]
    river_is_above_warning: Optional[bool]
    river_is_above_danger: Optional[bool]

    dam_data: Optional[List[Dict[str, Any]]]
    max_dam_discharge_cusecs: Optional[float]

    gis_evacuation_data: Optional[Dict[str, Any]]
    gis_evacuation_output: Optional[Dict[str, Any]]
    village_elevation_meters: Optional[float]
    is_low_lying_zone: Optional[bool]

    # Evidence pool and validation
    evidence_pool: Annotated[List[Dict[str, Any]], add_evidence_reducer]
    is_valid_for_assessment: Optional[bool]
    validation_summary: Optional[Dict[str, Any]]
    schema_validation_status: Optional[str]
    evidence_sufficiency_status: Optional[str]
    excluded_evidence: Optional[List[Dict[str, Any]]]

    # Deterministic risk engine outputs
    assessment_id: Optional[str]
    overall_risk: Optional[str]
    outlooks: Optional[Dict[str, Any]]
    triggered_rules: Optional[List[str]]
    explanation: Optional[str]
    assessment_mode: Optional[str]
    assessment_status: Optional[str]
    confidence_status: Optional[str]
    confidence_score: Optional[float]

    # Advisory & Dispatch
    alert_draft: Optional[Dict[str, Any]]
    alert_draft_id: Optional[str]

    # Audit, Tracing, Caveats
    agent_traces: Annotated[Dict[str, Any], update_traces_reducer]
    limitations: Annotated[List[str], add_errors_reducer]
    warnings: Annotated[List[str], add_errors_reducer]
    errors: Annotated[List[str], add_errors_reducer]
    status: Optional[str]
