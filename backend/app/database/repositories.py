"""Repository classes providing clean data access for ORM models."""

import math
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from backend.app.database.models import (
    Village,
    DataSource,
    EvidenceRecord,
    FloodAssessment,
    VillageRiskOutlook,
    AgentExecution,
    ReliefCentre,
    EvacuationRoute,
    ResidentReport,
    AlertDraft,
    AlertApproval,
    AuditLog,
)


class VillageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, village_id: str) -> Optional[Village]:
        return self.db.query(Village).filter(Village.id == village_id).first()

    def get_by_name(self, name: str) -> Optional[Village]:
        return self.db.query(Village).filter(Village.name.ilike(f"%{name.strip()}%")).first()

    def get_all(self, limit: int = 100) -> List[Village]:
        return self.db.query(Village).filter(Village.is_active == True).limit(limit).all()

    def create(self, village: Village) -> Village:
        self.db.add(village)
        self.db.commit()
        self.db.refresh(village)
        return village

    def find_nearest(self, lat: float, lon: float) -> Optional[Village]:
        """Find the nearest village using Euclidean approximation (adequate for regional scale)."""
        villages = self.get_all()
        if not villages:
            return None

        def dist(v: Village):
            return math.hypot(v.latitude - lat, v.longitude - lon)

        return min(villages, key=dist)


class AssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_assessment(
        self,
        assessment: FloodAssessment,
        outlooks: List[VillageRiskOutlook],
        evidence_records: List[EvidenceRecord],
    ) -> FloodAssessment:
        self.db.add(assessment)
        self.db.flush()
        for outlook in outlooks:
            outlook.assessment_id = assessment.id
            self.db.add(outlook)
        for ev in evidence_records:
            ev.assessment_id = assessment.id
            self.db.add(ev)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def get_by_id(self, assessment_id: str) -> Optional[FloodAssessment]:
        return self.db.query(FloodAssessment).filter(FloodAssessment.id == assessment_id).first()

    def get_latest_by_village(self, village_id: str) -> Optional[FloodAssessment]:
        return (
            self.db.query(FloodAssessment)
            .filter(FloodAssessment.village_id == village_id)
            .order_by(FloodAssessment.created_at.desc())
            .first()
        )


class AgentExecutionRepository:
    def __init__(self, db: Session):
        self.db = db

    def record_execution(self, execution: AgentExecution) -> AgentExecution:
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def get_by_run_id(self, run_id: str) -> List[AgentExecution]:
        return self.db.query(AgentExecution).filter(AgentExecution.run_id == run_id).all()


class ReliefCentreRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, district: Optional[str] = None) -> List[ReliefCentre]:
        query = self.db.query(ReliefCentre).filter(ReliefCentre.is_active == True)
        if district:
            query = query.filter(ReliefCentre.district.ilike(f"%{district.strip()}%"))
        return query.all()

    def create(self, centre: ReliefCentre) -> ReliefCentre:
        self.db.add(centre)
        self.db.commit()
        self.db.refresh(centre)
        return centre


class EvacuationRouteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_routes_for_village(self, village_id: str) -> List[EvacuationRoute]:
        return self.db.query(EvacuationRoute).filter(EvacuationRoute.origin_village_id == village_id).all()

    def create(self, route: EvacuationRoute) -> EvacuationRoute:
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route


class ResidentReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, report: ResidentReport) -> ResidentReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: str) -> Optional[ResidentReport]:
        return self.db.query(ResidentReport).filter(ResidentReport.id == report_id).first()

    def list_reports(self, status: Optional[str] = None, limit: int = 50) -> List[ResidentReport]:
        query = self.db.query(ResidentReport)
        if status:
            query = query.filter(ResidentReport.status == status)
        return query.order_by(ResidentReport.created_at.desc()).limit(limit).all()

    def update_review(
        self,
        report_id: str,
        status: str,
        reviewer_name: str,
        review_notes: Optional[str] = None,
    ) -> Optional[ResidentReport]:
        report = self.get_by_id(report_id)
        if not report:
            return None
        report.status = status
        report.reviewed_by = reviewer_name
        report.review_notes = review_notes
        report.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(report)
        return report


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_draft(self, draft: AlertDraft) -> AlertDraft:
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def get_by_id(self, alert_id: str) -> Optional[AlertDraft]:
        return self.db.query(AlertDraft).filter(AlertDraft.id == alert_id).first()

    def list_pending(self) -> List[AlertDraft]:
        return self.db.query(AlertDraft).filter(AlertDraft.status == "PENDING_APPROVAL").all()

    def record_approval(
        self,
        alert_id: str,
        approved_by: str,
        action: str,
        notes: Optional[str] = None,
    ) -> Optional[AlertDraft]:
        draft = self.get_by_id(alert_id)
        if not draft:
            return None

        approval = AlertApproval(
            alert_id=alert_id,
            approved_by=approved_by,
            action=action,
            notes=notes,
            approved_at=datetime.now(timezone.utc),
            dispatch_status="SUCCESS" if action == "APPROVE" else "CANCELLED",
        )
        self.db.add(approval)

        draft.status = "APPROVED" if action == "APPROVE" else "REJECTED"
        draft.approved_by = approved_by
        draft.approved_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(draft)
        return draft


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            details_json=details or {},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

