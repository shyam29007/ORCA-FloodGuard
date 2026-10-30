"""Integration tests for Master LangGraph Orchestrator and specialized workflows."""

from backend.app.orchestrator.graph import run_orchestrator
from backend.app.orchestrator.workflow import run_full_village_assessment
from backend.app.schemas.flood import RiskLevel


def test_full_orchestrator_execution():
    inputs = {
        "village_name": "Gidderpindi",
        "latitude": 31.1465,
        "longitude": 75.1872,
        "district": "Jalandhar",
        "forecast_horizon_hours": 72,
        "include_simulated_fallback": True,
    }
    state = run_orchestrator(inputs)

    # 1. State integrity
    assert state.get("status") == "COMPLETED"
    assert state.get("village_name") == "Gidderpindi"
    assert state.get("overall_risk") in ("LOW", "MODERATE", "HIGH", "CRITICAL", "INSUFFICIENT_EVIDENCE")

    # 2. Parallel fan-in evidence pool
    assert len(state.get("evidence_pool") or []) >= 4

    # 3. Agent traces captured
    traces = state.get("agent_traces") or {}
    assert "location_agent" in traces
    assert "weather_agent" in traces
    assert "river_agent" in traces
    assert "dam_agent" in traces
    assert "gis_evacuation_agent" in traces
    assert "alert_agent" in traces

    for agent_name, trace in traces.items():
        assert trace["status"] == "COMPLETED"
        assert trace["duration_ms"] >= 0.0

    # 4. Outook horizons
    outlooks = state.get("outlooks") or {}
    assert "24h" in outlooks
    assert "48h" in outlooks
    assert "72h" in outlooks

    # 5. Alert drafted
    alert_draft = state.get("alert_draft")
    assert alert_draft is not None
    assert alert_draft.get("status") == "PENDING_APPROVAL"


def test_conditional_routing_weather_only():
    inputs = {
        "workflow_type": "weather_only",
        "village_name": "Phillaur",
        "latitude": 31.0267,
        "longitude": 75.7871,
    }
    state = run_orchestrator(inputs)
    traces = state.get("agent_traces") or {}
    assert "weather_agent" in traces
    # River and Dam agents should be skipped
    assert "river_agent" not in traces
    assert "dam_agent" not in traces


def test_end_to_end_assessment_with_db_persistence(db_session):
    resp = run_full_village_assessment(
        village_name="Phillaur",
        latitude=31.0267,
        longitude=75.7871,
        district="Jalandhar",
        forecast_horizon_hours=72,
        include_simulated_fallback=True,
        db=db_session,
    )
    assert resp.assessment_id is not None
    assert resp.village.name == "Phillaur"
    assert resp.overall_risk in (RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert len(resp.contributing_evidence) > 0
    assert resp.alert_draft_id is not None

