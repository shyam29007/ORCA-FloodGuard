"""Resident crowd-sourced reporting and verification endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.reports import (
    ResidentReportCreate,
    ResidentReportReviewRequest,
    ResidentReportResponse,
)
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Resident Reports"])


@router.post("/upload", response_model=ApiResponse[ResidentReportResponse], status_code=status.HTTP_201_CREATED)
def upload_report(
    payload: ResidentReportCreate,
    db: Session = Depends(get_db),
):
    """Submit a ground-level observation report of localized flooding or river breach."""
    service = ReportService(db)
    res = service.submit_report(payload)
    return ApiResponse(
        success=True,
        message="Resident report submitted successfully",
        data=res,
    )


@router.get("/{report_id}", response_model=ApiResponse[ResidentReportResponse])
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details and review status of a submitted resident report."""
    service = ReportService(db)
    res = service.get_report(report_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return ApiResponse(success=True, data=res)


@router.post("/{report_id}/review", response_model=ApiResponse[ResidentReportResponse])
def review_report(
    report_id: str,
    review_req: ResidentReportReviewRequest,
    db: Session = Depends(get_db),
):
    """Review, verify, or flag a resident report (Disaster Management Authority workflow)."""
    service = ReportService(db)
    res = service.review_report(report_id, review_req)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return ApiResponse(
        success=True,
        message=f"Report status updated to '{res.status.value}'",
        data=res,
    )


@router.get("", response_model=ApiResponse[List[ResidentReportResponse]])
def list_reports(
    status_filter: Optional[str] = Query(None, description="Filter by status (PENDING, VERIFIED, REJECTED, FLAGGED)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent resident flood reports."""
    service = ReportService(db)
    reports = service.list_reports(status=status_filter, limit=limit)
    return ApiResponse(success=True, data=reports)

