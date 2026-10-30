"""Assessment application service coordinating orchestrator execution and DB persistence."""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.database.repositories import (
    AssessmentRepository,
    VillageRepository,
    AlertRepository,
    AgentExecutionRepository,
)
from backend.app.database.models import (
    FloodAssessment,
    VillageRiskOutlook,
    EvidenceRecord,
    AgentExecution,
    AlertDraft,
)
from backend.app.schemas.flood import FloodAssessmentResponse, RiskLevel, RiskOutlook
from backend.app.schemas.location import VillageLocation
from backend.app.schemas.evidence import EvidenceRecordSchema, ExcludedEvidenceRecord, EvidenceStatus, EvidenceQuality
from backend.app.schemas.evacuation import GISEvacuationAgentOutput
from backend.app.schemas.alerts import AlertDraftSchema, AlertChannel, AlertStatus
from backend.app.services.village_service import VillageService


class AssessmentService:
    def __init__(self, db: Session):
        self.db = db
        self.assessment_repo = AssessmentRepository(db)
        self.village_repo = VillageRepository(db)
        self.alert_repo = AlertRepository(db)
        self.agent_exec_repo = AgentExecutionRepository(db)
        self.village_service = VillageService(db)

    def persist_orchestrator_results(self, final_state: Dict[str, Any]) -> FloodAssessmentResponse:
        """Persist entire LangGraph orchestrator run results into PostgreSQL/SQLite."""
        run_id = final_state.get("run_id", "run-unknown")
        village_data = final_state.get("village", {})
        village_loc = VillageLocation(**village_data)

        # 1. Resolve or create Village entity
        village_entity = self.village_service.resolve_or_create(village_loc)

        # 2. Extract risk engine results and decoupled statuses
        overall_risk_str = final_state.get("overall_risk", "LOW")
        overall_risk = RiskLevel(overall_risk_str) if isinstance(overall_risk_str, str) else overall_risk_str
        explanation = final_state.get("explanation", "Assessment generated.")
        triggered_rules = final_state.get("triggered_rules", [])
        
        schema_val = final_state.get("schema_validation_status", "PASSED")
        ev_suff = final_state.get("evidence_sufficiency_status", "SUFFICIENT")
        assess_mode = final_state.get("assessment_mode", "OPERATIONAL")
        assess_status = final_state.get("assessment_status", "OPERATIONAL")
        conf_status = final_state.get("confidence_status", "NOT_CALIBRATED")
        # Ensure confidence_score is None when NOT_CALIBRATED; never substitute 0 or fabricated score
        conf_score = None if conf_status == "NOT_CALIBRATED" else final_state.get("confidence_score")
        limitations = final_state.get("limitations", [])
        warnings = final_state.get("warnings", [])
        excluded_raw = final_state.get("excluded_evidence", [])

        # 3. Create FloodAssessment entity
        fa_entity = FloodAssessment(
            run_id=run_id,
            village_id=village_entity.id,
            overall_risk=overall_risk.value,
            confidence_score=conf_score,  # None when NOT_CALIBRATED
            confidence_status=conf_status,
            validation_status=schema_val,
            schema_validation_status=schema_val,
            evidence_sufficiency_status=ev_suff,
            assessment_mode=assess_mode,
            assessment_status=assess_status,
            triggered_rules_json=triggered_rules,
            explanation=explanation,
            limitations_json=limitations,
            warnings_json=warnings,
            excluded_evidence_json=excluded_raw,
        )

        # 4. Create VillageRiskOutlook entities (24h, 48h, 72h)
        outlooks_raw = final_state.get("outlooks", {})
        outlook_entities: List[VillageRiskOutlook] = []
        for h, out in outlooks_raw.items():
            if isinstance(out, dict):
                o_status = out.get("confidence_status", "NOT_CALIBRATED")
                o_score = None if o_status == "NOT_CALIBRATED" else out.get("confidence_score")
                o_conf = None if o_status == "NOT_CALIBRATED" else out.get("confidence")
                o_rain = out.get("rainfall_forecast_mm")
                outlook_entities.append(
                    VillageRiskOutlook(
                        horizon=h,
                        risk_level=out.get("risk_level", "LOW"),
                        confidence=o_conf,
                        confidence_status=o_status,
                        confidence_score=o_score,
                        primary_factors_json=out.get("primary_factors", []),
                        triggered_rules_json=out.get("triggered_rules", []),
                        supporting_evidence_ids_json=out.get("supporting_evidence_ids", []),
                        rainfall_forecast_mm=float(o_rain) if o_rain is not None else None,
                        river_risk=out.get("river_proximity_risk", "NORMAL"),
                        dam_risk=out.get("dam_discharge_risk", "NORMAL"),
                    )
                )
            elif isinstance(out, RiskOutlook):
                o_status = out.confidence_status
                o_score = out.confidence_score
                o_conf = out.confidence
                o_rain = out.rainfall_forecast_mm
                outlook_entities.append(
                    VillageRiskOutlook(
                        horizon=h,
                        risk_level=out.risk_level.value if hasattr(out.risk_level, "value") else str(out.risk_level),
                        confidence=o_conf,
                        confidence_status=o_status,
                        confidence_score=o_score,
                        primary_factors_json=out.primary_factors,
                        triggered_rules_json=out.triggered_rules,
                        supporting_evidence_ids_json=out.supporting_evidence_ids,
                        rainfall_forecast_mm=float(o_rain) if o_rain is not None else None,
                        river_risk=out.river_proximity_risk,
                        dam_risk=out.dam_discharge_risk,
                    )
                )

        # 5. Create EvidenceRecord entities
        evidence_pool = final_state.get("evidence_pool", [])
        evidence_entities: List[EvidenceRecord] = []
        for ev in evidence_pool:
            evidence_entities.append(
                EvidenceRecord(
                    village_id=village_entity.id,
                    source=ev.get("source", "UNKNOWN"),
                    source_type=ev.get("source_type", "UNKNOWN"),
                    location_json=ev.get("location", {}),
                    parameter=ev.get("parameter", "unknown"),
                    value_num=float(ev["value"]) if isinstance(ev.get("value"), (int, float)) else None,
                    value_str=str(ev.get("value")) if not isinstance(ev.get("value"), (int, float, dict, list)) else None,
                    value_json=ev.get("value") if isinstance(ev.get("value"), (dict, list)) else None,
                    unit=ev.get("unit", ""),
                    observed_at=ev.get("observed_at"),
                    status=ev.get("status", "LIVE"),
                    quality=ev.get("quality", "HIGH"),
                    limitations=ev.get("limitations"),
                    validation_flags_json=ev.get("validation_flags", []),
                )
            )

        # 6. Save Assessment transactionally
        saved_fa = self.assessment_repo.create_assessment(
            assessment=fa_entity,
            outlooks=outlook_entities,
            evidence_records=evidence_entities,
        )

        # 7. Persist AgentExecution traces
        traces = final_state.get("agent_traces", {})
        for name, tr in traces.items():
            exec_entity = AgentExecution(
                run_id=run_id,
                assessment_id=saved_fa.id,
                agent_name=name,
                status=tr.get("status", "COMPLETED"),
                duration_ms=tr.get("duration_ms", 0.0),
                inputs_json=tr.get("inputs", {}),
                outputs_json=tr.get("outputs", {}),
                error_message=tr.get("error_message"),
            )
            self.agent_exec_repo.record_execution(exec_entity)

        # 8. Persist AlertDraft if created
        alert_draft_id = None
        alert_schema_obj = None
        alert_data = final_state.get("alert_draft")
        if alert_data:
            alert_entity = AlertDraft(
                id=alert_data.get("alert_id"),
                assessment_id=saved_fa.id,
                village_id=village_entity.id,
                village_name=village_entity.name,
                risk_level=alert_data.get("risk_level", overall_risk.value),
                headline=alert_data.get("headline", ""),
                english_text=alert_data.get("english_text", ""),
                punjabi_text=alert_data.get("punjabi_text", ""),
                recommended_action=alert_data.get("recommended_action", ""),
                target_channels_json=alert_data.get("target_channels", []),
                status=alert_data.get("status", "PENDING_APPROVAL"),
                evidence_summary_json=alert_data.get("evidence_summary", []),
            )
            self.alert_repo.create_draft(alert_entity)
            alert_draft_id = alert_entity.id
            alert_schema_obj = AlertDraftSchema(**alert_data)

        gis_out = None
        if "gis_evacuation_output" in final_state and final_state["gis_evacuation_output"]:
            gis_out = GISEvacuationAgentOutput(**final_state["gis_evacuation_output"])

        outlooks_map: Dict[str, RiskOutlook] = {
            k: (RiskOutlook(**v) if isinstance(v, dict) else v)
            for k, v in outlooks_raw.items()
        }

        return FloodAssessmentResponse(
            assessment_id=saved_fa.id,
            run_id=run_id,
            village=village_loc,
            overall_risk=overall_risk,
            outlooks=outlooks_map,
            schema_validation_status=schema_val,
            evidence_sufficiency_status=ev_suff,
            assessment_mode=assess_mode,
            assessment_status=assess_status,
            confidence_status=conf_status,
            confidence_score=conf_score,
            contributing_evidence=[EvidenceRecordSchema(**ev) for ev in evidence_pool],
            excluded_evidence=[ExcludedEvidenceRecord(**ex) for ex in excluded_raw],
            triggered_rules=triggered_rules,
            explanation=explanation,
            evacuation=gis_out,
            alert_draft_id=alert_draft_id,
            alert_draft=alert_schema_obj,
            limitations=limitations,
            warnings=warnings,
            validation_status=schema_val,
        )

    def get_assessment(self, assessment_id: str) -> Optional[FloodAssessmentResponse]:
        fa = self.assessment_repo.get_by_id(assessment_id)
        if not fa:
            return None

        village_loc = VillageLocation(
            village_id=fa.village.id,
            name=fa.village.name,
            name_pa=fa.village.name_pa,
            district=fa.village.district,
            tehsil=fa.village.tehsil,
            latitude=fa.village.latitude,
            longitude=fa.village.longitude,
            elevation_meters=fa.village.elevation_meters,
            river_basin=fa.village.river_basin,
            nearest_river=fa.village.nearest_river,
            distance_to_river_km=fa.village.distance_to_river_km,
            is_flood_prone=fa.village.is_flood_prone if fa.village.is_flood_prone is not None else True,
        )

        persisted_outlooks: Dict[str, RiskOutlook] = {}
        for o in fa.outlooks:
            persisted_outlooks[o.horizon] = RiskOutlook(
                horizon=o.horizon,
                risk_level=RiskLevel(o.risk_level),
                confidence_status=getattr(o, "confidence_status", "NOT_CALIBRATED"),
                confidence_score=getattr(o, "confidence_score", None),
                confidence=getattr(o, "confidence", None),
                primary_factors=list(o.primary_factors_json or []),
                triggered_rules=list(o.triggered_rules_json or []),
                supporting_evidence_ids=list(getattr(o, "supporting_evidence_ids_json", []) or []),
                rainfall_forecast_mm=o.rainfall_forecast_mm,
                river_proximity_risk=o.river_risk,
                dam_discharge_risk=o.dam_risk,
            )

        evidence_list: List[EvidenceRecordSchema] = []
        for ev in fa.evidence_records:
            evidence_list.append(
                EvidenceRecordSchema(
                    evidence_id=ev.id,
                    source=ev.source,
                    source_type=ev.source_type,
                    location=ev.location_json or {},
                    parameter=ev.parameter,
                    value=ev.value_num if ev.value_num is not None else ev.value_str,
                    unit=ev.unit,
                    observed_at=ev.observed_at,
                    status=EvidenceStatus(ev.status),
                    quality=EvidenceQuality(ev.quality),
                    limitations=ev.limitations,
                )
            )

        alert_id = fa.alert_drafts[0].id if fa.alert_drafts else None
        alert_obj = None
        if fa.alert_drafts:
            ad = fa.alert_drafts[0]
            alert_obj = AlertDraftSchema(
                alert_id=ad.id,
                assessment_id=ad.assessment_id,
                village_id=ad.village_id,
                village_name=ad.village_name,
                risk_level=RiskLevel(ad.risk_level),
                headline=ad.headline,
                english_text=ad.english_text,
                punjabi_text=ad.punjabi_text,
                recommended_action=ad.recommended_action,
                target_channels=[AlertChannel(c) for c in (ad.target_channels_json or [])],
                status=AlertStatus(ad.status),
                evidence_summary=list(ad.evidence_summary_json or []),
                created_at=ad.created_at,
                approved_by=ad.approved_by,
                approved_at=ad.approved_at,
            )

        excluded_list = [
            ExcludedEvidenceRecord(**ex) for ex in (getattr(fa, "excluded_evidence_json", []) or [])
        ]

        return FloodAssessmentResponse(
            assessment_id=fa.id,
            run_id=fa.run_id,
            village=village_loc,
            overall_risk=RiskLevel(fa.overall_risk),
            outlooks=persisted_outlooks,
            schema_validation_status=getattr(fa, "schema_validation_status", "PASSED") or "PASSED",
            evidence_sufficiency_status=getattr(fa, "evidence_sufficiency_status", "SUFFICIENT") or "SUFFICIENT",
            assessment_mode=getattr(fa, "assessment_mode", "OPERATIONAL") or "OPERATIONAL",
            assessment_status=getattr(fa, "assessment_status", "OPERATIONAL") or "OPERATIONAL",
            confidence_status=getattr(fa, "confidence_status", "NOT_CALIBRATED") or "NOT_CALIBRATED",
            confidence_score=getattr(fa, "confidence_score", None),
            contributing_evidence=evidence_list,
            excluded_evidence=excluded_list,
            triggered_rules=fa.triggered_rules_json or [],
            explanation=fa.explanation,
            alert_draft_id=alert_id,
            alert_draft=alert_obj,
            limitations=getattr(fa, "limitations_json", []) or [],
            warnings=getattr(fa, "warnings_json", []) or [],
            validation_status=getattr(fa, "validation_status", "PASSED") or "PASSED",
        )

    def get_latest_outlook_for_village(self, village_id: str) -> Optional[Dict[str, Any]]:
        fa = self.assessment_repo.get_latest_by_village(village_id)
        if not fa:
            return None
        return {
            "village_id": village_id,
            "village_name": fa.village.name,
            "overall_risk": fa.overall_risk,
            "assessed_at": fa.created_at.isoformat(),
            "confidence_status": getattr(fa, "confidence_status", "NOT_CALIBRATED"),
            "confidence_score": getattr(fa, "confidence_score", None),
            "outlooks": {
                o.horizon: {
                    "risk_level": o.risk_level,
                    "confidence_status": getattr(o, "confidence_status", "NOT_CALIBRATED"),
                    "confidence_score": getattr(o, "confidence_score", None),
                    "rainfall_forecast_mm": o.rainfall_forecast_mm,
                    "primary_factors": o.primary_factors_json or [],
                }
                for o in fa.outlooks
            },
        }
