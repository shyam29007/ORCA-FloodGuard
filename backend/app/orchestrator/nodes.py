"""Node implementations for LangGraph Master Orchestrator."""

import uuid
from typing import Dict, Any, List, Optional
from backend.app.orchestrator.state import MasterOrchestratorState
from backend.app.agents.location_agent import LocationAgent
from backend.app.agents.weather_agent import WeatherAgent
from backend.app.agents.river_agent import RiverAgent
from backend.app.agents.dam_agent import DamAgent
from backend.app.agents.gis_evacuation_agent import GISEvacuationAgent
from backend.app.agents.alert_agent import AlertAgent
from backend.app.services.evidence_normalizer import EvidenceNormalizer
from backend.app.services.evidence_validator import EvidenceValidator
from backend.app.services.risk_assessment import DeterministicRiskEngine
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceCollectionSummary
from backend.app.schemas.agents import AgentExecutionTrace
from backend.app.core.logging import logger


def _format_trace(trace: Any) -> Optional[Dict[str, Any]]:
    if isinstance(trace, AgentExecutionTrace):
        return {trace.agent_name.value: trace.model_dump()}
    if isinstance(trace, dict):
        agent_name = str(trace.get("agent_name", "agent"))
        return {agent_name: trace}
    return None


def validate_input_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Validate initial assessment request parameters."""
    run_id = state.get("run_id") or f"run-{uuid.uuid4().hex[:12]}"
    workflow_type = state.get("workflow_type") or "full"
    forecast_horizon = state.get("forecast_horizon_hours") or 72
    operational_mode = state.get("operational_mode", False)

    logger.info("[ValidateInputNode] Initializing run %s (workflow: %s, operational: %s)",
                run_id, workflow_type, operational_mode)
    return {
        "run_id": run_id,
        "workflow_type": workflow_type,
        "forecast_horizon_hours": forecast_horizon,
        "operational_mode": operational_mode,
        "errors": [],
        "warnings": [],
        "limitations": [],
    }


def location_agent_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Execute Location Agent to resolve village coordinates and river basin."""
    agent = LocationAgent()
    res = agent.run(dict(state), run_id=state.get("run_id"))
    trace = res.pop("_trace", None)
    updates: Dict[str, Any] = {
        "village": res.get("village"),
        "location_resolution": res.get("location_resolution"),
        "latitude": res.get("latitude"),
        "longitude": res.get("longitude"),
        "village_name": res.get("village_name"),
        "district": res.get("district"),
        "river_basin": res.get("river_basin"),
    }
    trace_dict = _format_trace(trace)
    if trace_dict:
        updates["agent_traces"] = trace_dict
    return updates


def weather_agent_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Execute Weather Agent to retrieve rainfall forecasts."""
    agent = WeatherAgent()
    res = agent.run(dict(state), run_id=state.get("run_id"))
    trace = res.pop("_trace", None)
    ev_records = res.get("evidence_records", [])

    updates: Dict[str, Any] = {
        "weather_data": res.get("weather_data"),
        "rainfall_24h_mm": res.get("rainfall_24h_mm"),
        "rainfall_48h_mm": res.get("rainfall_48h_mm"),
        "rainfall_72h_mm": res.get("rainfall_72h_mm"),
        "evidence_pool": ev_records,
    }
    trace_dict = _format_trace(trace)
    if trace_dict:
        updates["agent_traces"] = trace_dict
    return updates


def river_agent_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Execute River Agent to retrieve CWC station telemetry."""
    agent = RiverAgent()
    res = agent.run(dict(state), run_id=state.get("run_id"))
    trace = res.pop("_trace", None)
    ev_records = res.get("evidence_records", [])

    updates: Dict[str, Any] = {
        "river_data": res.get("river_data"),
        "river_level_meters": res.get("river_level_meters"),
        "river_is_above_warning": bool(res.get("river_is_above_warning", False)),
        "river_is_above_danger": bool(res.get("river_is_above_danger", False)),
        "evidence_pool": ev_records,
    }
    trace_dict = _format_trace(trace)
    if trace_dict:
        updates["agent_traces"] = trace_dict
    return updates


def dam_agent_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Execute Dam Agent to retrieve reservoir discharge rates."""
    agent = DamAgent()
    res = agent.run(dict(state), run_id=state.get("run_id"))
    trace = res.pop("_trace", None)
    ev_records = res.get("evidence_records", [])

    updates: Dict[str, Any] = {
        "dam_data": res.get("dam_data"),
        "max_dam_discharge_cusecs": float(res.get("max_dam_discharge_cusecs") or 0.0),
        "evidence_pool": ev_records,
    }
    trace_dict = _format_trace(trace)
    if trace_dict:
        updates["agent_traces"] = trace_dict
    return updates


def gis_evacuation_agent_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Execute GIS & Evacuation Agent to calculate routes and relief shelter capacities."""
    agent = GISEvacuationAgent()
    res = agent.run(dict(state), run_id=state.get("run_id"))
    trace = res.pop("_trace", None)
    ev_records = res.get("evidence_records", [])

    updates: Dict[str, Any] = {
        "gis_evacuation_data": res.get("gis_evacuation_data"),
        "gis_evacuation_output": res.get("gis_evacuation_output"),
        "village_elevation_meters": res.get("village_elevation_meters"),
        "is_low_lying_zone": bool(res.get("is_low_lying_zone", False)),
        "evidence_pool": ev_records,
    }
    trace_dict = _format_trace(trace)
    if trace_dict:
        updates["agent_traces"] = trace_dict
    if res.get("warnings"):
        updates["warnings"] = list(res["warnings"])
    return updates


def evidence_normalization_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Deduplicate and normalize all gathered evidence in the shared pool."""
    pool = state.get("evidence_pool") or []
    records = [EvidenceRecordSchema(**r) for r in pool if isinstance(r, dict)]
    deduped = EvidenceNormalizer.deduplicate(records)
    logger.info("[EvidenceNormalizationNode] Normalized %d raw records into %d unique items", len(pool), len(deduped))
    return {
        "evidence_pool": [r.model_dump() for r in deduped],
        "schema_validation_status": "PASSED",
    }


def evidence_validation_gate_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Enforce evidence validation gate before deterministic risk evaluation."""
    pool = state.get("evidence_pool") or []
    allow_simulated = bool(state.get("include_simulated_fallback", True))
    operational_mode = bool(state.get("operational_mode", False))
    records = [EvidenceRecordSchema(**r) for r in pool if isinstance(r, dict)]

    is_valid, summary, contributing, excluded = EvidenceValidator.validate_collection(
        records,
        allow_simulated=allow_simulated,
        operational_mode=operational_mode,
    )

    logger.info(
        "[ValidationGate] Gate result: is_valid=%s, sufficiency=%s (live=%d, sim=%d, static=%d, missing=%s)",
        is_valid, summary.sufficiency_status, summary.live_count, summary.simulated_count,
        summary.static_reference_count, summary.critical_missing
    )

    return {
        "is_valid_for_assessment": is_valid,
        "schema_validation_status": "PASSED",
        "evidence_sufficiency_status": summary.sufficiency_status,
        "validation_summary": summary.model_dump(),
        "evidence_pool": [c.model_dump() for c in contributing],
        "excluded_evidence": [ex.model_dump() for ex in excluded],
    }


def deterministic_risk_assessment_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Run separate Python deterministic risk engine across 24h, 48h, and 72h horizons."""
    village = state.get("village") or {}
    village_name: str = str(village.get("name") or state.get("village_name") or "Village")
    dist_river: float = float(village.get("distance_to_river_km") or 2.0)
    is_low_lying: bool = bool(state.get("is_low_lying_zone") or False)

    summary_dict = state.get("validation_summary") or {}
    val_summary = EvidenceCollectionSummary(**summary_dict) if summary_dict else EvidenceCollectionSummary()

    pool = state.get("evidence_pool") or []
    contributing = [EvidenceRecordSchema(**r) for r in pool if isinstance(r, dict)]

    river_data = state.get("river_data") or {}
    reading = river_data.get("reading") or {}
    buffer_val = reading.get("buffer_to_danger_meters")
    river_buffer: Optional[float] = float(buffer_val) if buffer_val is not None else None
    operational_mode: bool = bool(state.get("operational_mode") or False)

    r24 = state.get("rainfall_24h_mm")
    r48 = state.get("rainfall_48h_mm")
    r72 = state.get("rainfall_72h_mm")

    overall_risk, outlooks, triggered_rules, explanation, assessment_mode, assessment_status, limitations = (
        DeterministicRiskEngine.assess_village_risk(
            village_name=village_name,
            distance_to_river_km=dist_river,
            is_low_lying=is_low_lying,
            rainfall_24h_mm=float(r24) if r24 is not None else None,
            rainfall_48h_mm=float(r48) if r48 is not None else None,
            rainfall_72h_mm=float(r72) if r72 is not None else None,
            river_above_warning=bool(state.get("river_is_above_warning") or False),
            river_above_danger=bool(state.get("river_is_above_danger") or False),
            river_buffer_to_danger=river_buffer,
            max_dam_discharge_cusecs=float(state.get("max_dam_discharge_cusecs") or 0.0),
            validation_summary=val_summary,
            contributing_evidence=contributing,
            operational_mode=operational_mode,
        )
    )

    assessment_id = f"fa-{uuid.uuid4().hex[:8]}"

    return {
        "assessment_id": assessment_id,
        "overall_risk": overall_risk.value,
        "outlooks": {k: v.model_dump() for k, v in outlooks.items()},
        "triggered_rules": triggered_rules,
        "explanation": explanation,
        "assessment_mode": assessment_mode,
        "assessment_status": assessment_status,
        "confidence_status": "NOT_CALIBRATED",
        "confidence_score": None,
        "limitations": limitations,
    }


def alert_agent_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """Execute Alert Agent to generate bilingual draft advisory."""
    agent = AlertAgent()
    alert_input_state = dict(state)
    
    # If simulated demo, prefix in alert input so text reflects simulation
    if state.get("assessment_mode") == "SIMULATION_DEMO":
        alert_input_state["is_simulated_demo"] = True

    res = agent.run(alert_input_state, run_id=state.get("run_id"))
    trace = res.pop("_trace", None)

    draft = res.get("alert_draft")
    draft_id: Optional[str] = None
    if isinstance(draft, dict):
        if state.get("assessment_mode") == "SIMULATION_DEMO":
            draft["headline"] = f"[DEMO] {draft.get('headline', '')}"
            draft["english_text"] = f"[SIMULATION SCENARIO - NOT AN ACTIVE WARNING] {draft.get('english_text', '')}"
            draft["punjabi_text"] = f"[ਸਿਮੂਲੇਸ਼ਨ ਪ੍ਰਦਰਸ਼ਨ - ਅਸਲ ਚੇਤਾਵਨੀ ਨਹੀਂ] {draft.get('punjabi_text', '')}"
        if draft.get("alert_id") is not None:
            draft_id = str(draft["alert_id"])

    updates: Dict[str, Any] = {
        "alert_draft": draft,
        "alert_draft_id": draft_id,
        "status": "COMPLETED",
    }
    trace_dict = _format_trace(trace)
    if trace_dict:
        updates["agent_traces"] = trace_dict
    return updates
