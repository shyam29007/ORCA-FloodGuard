"""Workflow entrypoints and specialized pipeline runners."""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.orchestrator.graph import run_orchestrator, master_orchestrator
from backend.app.orchestrator.state import MasterOrchestratorState
from backend.app.services.assessment_service import AssessmentService
from backend.app.schemas.flood import FloodAssessmentResponse, RiskLevel, RiskOutlook
from backend.app.schemas.location import VillageLocation
from backend.app.schemas.evidence import EvidenceRecordSchema, ExcludedEvidenceRecord
from backend.app.schemas.evacuation import GISEvacuationAgentOutput
from backend.app.schemas.alerts import AlertDraftSchema


def run_full_village_assessment(
    village_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    district: Optional[str] = None,
    forecast_horizon_hours: int = 72,
    include_simulated_fallback: bool = True,
    operational_mode: bool = False,
    db: Optional[Session] = None,
) -> FloodAssessmentResponse:
    """Execute complete end-to-end village assessment, validate evidence, compute risk, draft alert, and persist."""
    inputs = {
        "workflow_type": "full",
        "village_name": village_name,
        "latitude": latitude,
        "longitude": longitude,
        "district": district,
        "forecast_horizon_hours": forecast_horizon_hours,
        "include_simulated_fallback": include_simulated_fallback,
        "operational_mode": operational_mode,
    }

    final_state = run_orchestrator(inputs)

    if db is not None:
        service = AssessmentService(db)
        return service.persist_orchestrator_results(dict(final_state))

    # In-memory return if no DB session supplied
    village_data = final_state.get("village") or {
        "name": village_name or "Unknown Village",
        "district": district or "Punjab",
        "latitude": latitude if latitude is not None else 31.0,
        "longitude": longitude if longitude is not None else 75.0,
    }
    village_loc = VillageLocation(**village_data)
    overall_risk = RiskLevel(str(final_state.get("overall_risk") or "LOW"))

    gis_out = None
    gis_data = final_state.get("gis_evacuation_output")
    if gis_data and isinstance(gis_data, dict):
        gis_out = GISEvacuationAgentOutput(**gis_data)

    alert_draft_obj = None
    raw_draft = final_state.get("alert_draft")
    if raw_draft and isinstance(raw_draft, dict):
        alert_draft_obj = AlertDraftSchema(**raw_draft)

    raw_outlooks = final_state.get("outlooks") or {}
    outlooks_dict: Dict[str, RiskOutlook] = {}
    if isinstance(raw_outlooks, dict):
        for k, v in raw_outlooks.items():
            if isinstance(v, RiskOutlook):
                outlooks_dict[k] = v
            elif isinstance(v, dict):
                outlooks_dict[k] = RiskOutlook(**v)

    return FloodAssessmentResponse(
        assessment_id=str(final_state.get("assessment_id") or "fa-temp"),
        run_id=str(final_state.get("run_id") or "run-temp"),
        village=village_loc,
        overall_risk=overall_risk,
        outlooks=outlooks_dict,
        schema_validation_status=str(final_state.get("schema_validation_status") or "PASSED"),
        evidence_sufficiency_status=str(final_state.get("evidence_sufficiency_status") or "SUFFICIENT"),
        assessment_mode=str(final_state.get("assessment_mode") or "OPERATIONAL"),
        assessment_status=str(final_state.get("assessment_status") or "OPERATIONAL"),
        confidence_status=str(final_state.get("confidence_status") or "NOT_CALIBRATED"),
        confidence_score=final_state.get("confidence_score"),
        contributing_evidence=[EvidenceRecordSchema(**ev) for ev in (final_state.get("evidence_pool") or [])],
        excluded_evidence=[ExcludedEvidenceRecord(**ex) for ex in (final_state.get("excluded_evidence") or [])],
        triggered_rules=list(final_state.get("triggered_rules") or []),
        explanation=str(final_state.get("explanation") or ""),
        evacuation=gis_out,
        alert_draft_id=final_state.get("alert_draft_id"),
        alert_draft=alert_draft_obj,
        limitations=list(final_state.get("limitations") or []),
        warnings=list(final_state.get("warnings") or []),
        validation_status=str(final_state.get("schema_validation_status") or "PASSED"),
    )
