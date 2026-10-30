"""Alert draft lifecycle, human approval, and dispatch service."""

from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.database.repositories import AlertRepository
from backend.app.database.models import AlertDraft
from backend.app.schemas.alerts import (
    AlertDraftSchema,
    AlertApprovalRequest,
    AlertApprovalResponse,
    AlertStatus,
    AlertChannel,
)
from backend.app.schemas.common import RiskLevel
from backend.app.tools.notification_tool import dispatch_alert
from backend.app.core.exceptions import AlertNotFoundException


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AlertRepository(db)

    def get_alert(self, alert_id: str) -> Optional[AlertDraftSchema]:
        draft = self.repo.get_by_id(alert_id)
        if not draft:
            return None
        return AlertDraftSchema(
            alert_id=draft.id,
            assessment_id=draft.assessment_id,
            village_id=draft.village_id,
            village_name=draft.village_name,
            risk_level=RiskLevel(draft.risk_level),
            headline=draft.headline,
            english_text=draft.english_text,
            punjabi_text=draft.punjabi_text,
            recommended_action=draft.recommended_action,
            target_channels=[AlertChannel(c) for c in (draft.target_channels_json or [])],
            status=AlertStatus(draft.status),
            evidence_summary=list(draft.evidence_summary_json or []),
            created_at=draft.created_at,
            approved_by=draft.approved_by,
            approved_at=draft.approved_at,
        )

    def list_pending_alerts(self) -> List[AlertDraftSchema]:
        drafts = self.repo.list_pending()
        return [
            AlertDraftSchema(
                alert_id=d.id,
                assessment_id=d.assessment_id,
                village_id=d.village_id,
                village_name=d.village_name,
                risk_level=RiskLevel(d.risk_level),
                headline=d.headline,
                english_text=d.english_text,
                punjabi_text=d.punjabi_text,
                recommended_action=d.recommended_action,
                target_channels=[AlertChannel(c) for c in (d.target_channels_json or [])],
                status=AlertStatus(d.status),
                evidence_summary=list(d.evidence_summary_json or []),
                created_at=d.created_at,
                approved_by=d.approved_by,
                approved_at=d.approved_at,
            )
            for d in drafts
        ]

    def process_approval(self, req: AlertApprovalRequest) -> AlertApprovalResponse:
        draft = self.repo.get_by_id(req.alert_id)
        if not draft:
            raise AlertNotFoundException(f"Alert draft {req.alert_id} not found.")

        updated = self.repo.record_approval(
            alert_id=req.alert_id,
            approved_by=req.approved_by,
            action=req.action,
            notes=req.modification_notes,
        )
        if not updated:
            raise AlertNotFoundException(f"Failed to record approval for alert {req.alert_id}")

        dispatch_results = None
        if req.action.upper() == "APPROVE":
            alert_schema = self.get_alert(req.alert_id)
            if alert_schema:
                alert_schema.status = AlertStatus.APPROVED
                dispatch_results = dispatch_alert(alert_schema)

        return AlertApprovalResponse(
            alert_id=updated.id,
            status=AlertStatus(updated.status),
            action_taken=req.action.upper(),
            approved_by=req.approved_by,
            dispatch_results=dispatch_results,
        )

