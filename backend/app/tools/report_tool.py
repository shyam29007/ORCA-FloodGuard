"""Resident crowd-sourced reporting tool."""

from typing import Dict, Any, List
from backend.app.schemas.reports import ResidentReportCreate, ResidentReportResponse, ReportStatus


def validate_report_submission(report: ResidentReportCreate) -> Dict[str, Any]:
    """Validate citizen report data and coordinates."""
    errors: List[str] = []
    if not (29.5 <= report.latitude <= 32.5 and 73.5 <= report.longitude <= 77.0):
        errors.append("Coordinates are outside Punjab state boundaries.")
    if report.water_level_inches is not None and report.water_level_inches > 300:
        errors.append("Unrealistic water level reported (> 300 inches).")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
    }

