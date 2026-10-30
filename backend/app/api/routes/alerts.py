"""Flood warning draft and human approval endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.alerts import (
    AlertDraftSchema,
    AlertApprovalRequest,
    AlertApprovalResponse,
)
from backend.app.agents.alert_agent import AlertAgent
from backend.app.services.alert_service import AlertService
from backend.app.database.repositories import VillageRepository, AssessmentRepository
from backend.app.database.models import AlertDraft

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/draft", response_model=ApiResponse[AlertDraftSchema], status_code=status.HTTP_201_CREATED)
def draft_alert(
    village_name: str,
    overall_risk: str = "HIGH",
    rainfall_24h_mm: float = 65.0,
    db: Session = Depends(get_db),
):
    """Generate a village-specific bilingual advisory draft for human official review."""
    agent = AlertAgent()
    state = {
        "village_name": village_name,
        "overall_risk": overall_risk,
        "rainfall_24h_mm": rainfall_24h_mm,
        "evidence_summary": [f"Precipitation: {rainfall_24h_mm}mm in 24h"],
    }
    agent_res = agent.run(state)
    draft_dict = agent_res.get("alert_draft")
    if not draft_dict:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate alert draft.",
        )

    # Persist draft
    service = AlertService(db)
    v_repo = VillageRepository(db)
    v = v_repo.get_by_name(village_name)
    v_id = v.id if v else f"vil-{village_name.lower()}"

    draft_model = AlertDraft(
        id=draft_dict["alert_id"],
        assessment_id=draft_dict["assessment_id"],
        village_id=v_id,
        village_name=village_name,
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
    db: Session = Depends(get_db),
):
    """Human approval gate: Authorize or reject alert dissemination to citizens."""
    if approval_req.alert_id != alert_id:
        approval_req.alert_id = alert_id

    service = AlertService(db)
    resp = service.process_approval(approval_req)
    return ApiResponse(
        success=True,
        message=f"Alert {alert_id} successfully {resp.action_taken}",
        data=resp,
    )

