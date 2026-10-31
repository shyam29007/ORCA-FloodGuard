"""Flood warning draft and human approval endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.core.auth import require_role
from backend.app.core.logging import logger
from backend.app.schemas.auth import UserRole, UserProfile
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.alerts import (
    AlertDraftSchema,
    AlertApprovalRequest,
    AlertApprovalResponse,
)
from backend.app.agents.alert_agent import AlertAgent
from backend.app.services.alert_service import AlertService
from backend.app.database.repositories import VillageRepository, AssessmentRepository, AuditLogRepository
from backend.app.database.models import AlertDraft

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/draft", response_model=ApiResponse[AlertDraftSchema], status_code=status.HTTP_201_CREATED)
def draft_alert(
    assessment_id: str = Query(..., description="UUID of existing persisted flood assessment"),
    village_name: Optional[str] = Query(None, description="Optional override village name"),
    overall_risk: Optional[str] = Query(None, description="Optional override risk level (e.g. HIGH, CRITICAL)"),
    rainfall_24h_mm: float = Query(65.0, description="Cumulative 24h rainfall in mm"),
    db: Session = Depends(get_db),
):
    """Generate a village-specific bilingual advisory draft linked to a verified assessment."""
    assess_repo = AssessmentRepository(db)
    assessment = assess_repo.get_by_id(assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found. Cannot draft alert without a valid persisted assessment.",
        )

    vil_name = village_name or (assessment.village.name if assessment.village else "Phillaur")
    vil_id = assessment.village_id
    risk = overall_risk or (assessment.overall_risk.value if hasattr(assessment.overall_risk, "value") else str(assessment.overall_risk))

    agent = AlertAgent()
    state = {
        "village_name": vil_name,
        "village": {"village_id": vil_id, "name": vil_name},
        "overall_risk": risk,
        "rainfall_24h_mm": rainfall_24h_mm,
        "assessment_id": assessment.id,
        "evidence_summary": [f"Precipitation: {rainfall_24h_mm}mm in 24h (Assessment: {assessment.id})"],
    }
    agent_res = agent.run(state)
    draft_dict = agent_res.get("alert_draft")
    if not draft_dict:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate alert draft.",
        )

    # Persist draft with real foreign keys
    draft_model = AlertDraft(
        id=draft_dict["alert_id"],
        assessment_id=assessment.id,
        village_id=vil_id,
        village_name=vil_name,
        risk_level=draft_dict["risk_level"],
        headline=draft_dict["headline"],
        english_text=draft_dict["english_text"],
        punjabi_text=draft_dict["punjabi_text"],
        recommended_action=draft_dict["recommended_action"],
        target_channels_json=draft_dict["target_channels"],
        status="PENDING_APPROVAL",
        evidence_summary_json=draft_dict["evidence_summary"],
    )
    db.add(draft_model)
    db.commit()

    return ApiResponse(
        success=True,
        message="Alert draft prepared and awaiting human approval.",
        data=AlertDraftSchema(**draft_dict),
    )


@router.get("/pending", response_model=ApiResponse[List[AlertDraftSchema]])
def list_pending_alerts(db: Session = Depends(get_db)):
    """List all alert drafts awaiting official review."""
    service = AlertService(db)
    drafts = service.list_pending_alerts()
    return ApiResponse(success=True, data=drafts)


@router.get("/{alert_id}", response_model=ApiResponse[AlertDraftSchema])
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Retrieve details and review status of an alert draft."""
    service = AlertService(db)
    alert = service.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    return ApiResponse(success=True, data=alert)


@router.post("/{alert_id}/approve", response_model=ApiResponse[AlertApprovalResponse])
def approve_alert(
    alert_id: str,
    approval_req: AlertApprovalRequest,
    current_user: UserProfile = Depends(require_role([UserRole.OFFICIAL, UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Human approval gate: Authorize or reject alert dissemination to citizens."""
    if approval_req.alert_id != alert_id:
        approval_req.alert_id = alert_id

    # Enforce approver identity from authenticated official/admin token
    approver_identity = f"{current_user.full_name} ({current_user.role.value})"
    approval_req.approved_by = approver_identity

    service = AlertService(db)
    resp = service.process_approval(approval_req)

    # Record audit log trail
    try:
        audit_repo = AuditLogRepository(db)
        audit_repo.log(
            entity_type="ALERT",
            entity_id=alert_id,
            action=approval_req.action.upper(),
            actor=current_user.email,
            details={
                "action_taken": resp.action_taken,
                "approved_by": approval_req.approved_by,
                "role": current_user.role.value,
                "modification_notes": approval_req.modification_notes,
            },
        )
    except Exception as e:
        logger.warning("Failed to record audit log for alert %s approval: %s", alert_id, str(e))

    return ApiResponse(
        success=True,
        message=f"Alert {alert_id} successfully {resp.action_taken}",
        data=resp,
    )
