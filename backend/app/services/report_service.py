"""Citizen and ground observation report service."""

from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.database.repositories import ResidentReportRepository
from backend.app.database.models import ResidentReport
from backend.app.schemas.reports import (
    ResidentReportCreate,
    ResidentReportReviewRequest,
    ResidentReportResponse,
    ReportStatus,
)
from backend.app.tools.report_tool import validate_report_submission


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ResidentReportRepository(db)

    def submit_report(self, payload: ResidentReportCreate) -> ResidentReportResponse:
        val = validate_report_submission(payload)
        status = "PENDING" if val["is_valid"] else "FLAGGED"

        entity = ResidentReport(
            village_name=payload.village_name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            water_level_inches=payload.water_level_inches,
            observations=payload.observations,
            reporter_name=payload.reporter_name or "Anonymous Citizen",
            contact_phone=payload.contact_phone,
            media_url=payload.media_url,
            status=status,
            review_notes="; ".join(val["errors"]) if val["errors"] else None,
        )
        saved = self.repo.create(entity)
        return self._to_schema(saved)

    def get_report(self, report_id: str) -> Optional[ResidentReportResponse]:
        rep = self.repo.get_by_id(report_id)
        if not rep:
            return None
        return self._to_schema(rep)

    def review_report(self, report_id: str, req: ResidentReportReviewRequest) -> Optional[ResidentReportResponse]:
        updated = self.repo.update_review(
            report_id=report_id,
            status=req.status.value,
            reviewer_name=req.reviewer_name,
            review_notes=req.review_notes,
        )
        if not updated:
            return None
        return self._to_schema(updated)

    def list_reports(self, status: Optional[str] = None, limit: int = 50) -> List[ResidentReportResponse]:
        records = self.repo.list_reports(status=status, limit=limit)
        return [self._to_schema(r) for r in records]

    def _to_schema(self, r: ResidentReport) -> ResidentReportResponse:
        return ResidentReportResponse(
            report_id=r.id,
            village_name=r.village_name,
            latitude=r.latitude,
            longitude=r.longitude,
            water_level_inches=r.water_level_inches,
            observations=r.observations,
            reporter_name=r.reporter_name,
            media_url=r.media_url,
            status=ReportStatus(r.status),
            created_at=r.created_at,
            reviewed_by=r.reviewed_by,
            reviewed_at=r.reviewed_at,
            review_notes=r.review_notes,
        )

