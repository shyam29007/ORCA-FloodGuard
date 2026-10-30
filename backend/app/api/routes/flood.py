"""Flood assessment endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.schemas.flood import FloodAssessmentRequest, FloodAssessmentResponse
from backend.app.schemas.common import ApiResponse
from backend.app.orchestrator.workflow import run_full_village_assessment
from backend.app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/flood", tags=["Flood Assessment"])


@router.post("/assess", response_model=ApiResponse[FloodAssessmentResponse])
def assess_flood_risk(
    req: FloodAssessmentRequest,
    db: Session = Depends(get_db),
):
    """Trigger agentic AI orchestrator to assess village flood risk across 24h, 48h, and 72h horizons."""
    lat = req.coordinates.latitude if req.coordinates else None
    lon = req.coordinates.longitude if req.coordinates else None

    result = run_full_village_assessment(
        village_name=req.village_name,
        latitude=lat,
        longitude=lon,
        district=req.district,
        forecast_horizon_hours=req.forecast_horizon_hours,
        include_simulated_fallback=req.include_simulated_fallback,
        operational_mode=req.operational_mode,
        db=db,
    )
    return ApiResponse(
        success=True,
        message=f"Assessment completed with overall risk '{result.overall_risk.value}'",
        data=result,
    )


@router.get("/assessments/{assessment_id}", response_model=ApiResponse[FloodAssessmentResponse])
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve an existing flood assessment by UUID."""
    service = AssessmentService(db)
    result = service.get_assessment(assessment_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found.",
        )
    return ApiResponse(success=True, data=result)


@router.get("/villages/{village_id}/outlook", response_model=ApiResponse[Dict[str, Any]])
def get_village_outlook(
    village_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve the latest risk outlook for a specific village."""
    service = AssessmentService(db)
    result = service.get_latest_outlook_for_village(village_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No assessment found for village '{village_id}'.",
        )
    return ApiResponse(success=True, data=result)

