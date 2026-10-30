"""Dam telemetry endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Query
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.dam import DamInformation
from backend.app.tools.dam_tool import fetch_dam_telemetry

router = APIRouter(prefix="/dam", tags=["Dam"])


@router.get("/information", response_model=ApiResponse[List[DamInformation]])
def get_dam_information(
    river_basin: Optional[str] = Query(None, description="Optional basin filter (e.g. Sutlej, Beas, Ravi)"),
    include_simulated: bool = Query(True, description="Allow simulated evidence fallback"),
):
    """Retrieve reservoir levels, live storage, and spillway release rates for major dams."""
    dams, _ = fetch_dam_telemetry(river_basin=river_basin, allow_simulated=include_simulated)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(dams)} dam telemetry records",
        data=dams,
    )

