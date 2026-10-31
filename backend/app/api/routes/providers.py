"""Provider status and telemetry dashboard endpoints."""

from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.provider import (
    ProviderHealthStatus,
    ProviderDashboardResponse,
)
from backend.app.integrations import (
    IMDWeatherProvider,
    CWCRiverProvider,
    BBMBDamProvider,
    check_all_providers_health_async,
)

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.get(
    "/status",
    response_model=ProviderDashboardResponse,
    summary="Get aggregated live provider connectivity and telemetry readiness",
)
async def get_providers_dashboard_status() -> ProviderDashboardResponse:
    """Return health, connectivity, authentication, and live telemetry readiness for all external providers."""
    return await check_all_providers_health_async()


@router.get(
    "/{provider_name}/health",
    response_model=ProviderHealthStatus,
    summary="Check health of a specific external telemetry provider",
)
async def get_single_provider_health(provider_name: str) -> ProviderHealthStatus:
    """Perform a health and live connectivity validation check for a designated external provider (imd, cwc, bbmb)."""
    normalized = provider_name.strip().lower()
    if normalized == "imd":
        provider = IMDWeatherProvider()
    elif normalized == "cwc":
        provider = CWCRiverProvider()
    elif normalized == "bbmb":
        provider = BBMBDamProvider()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown telemetry provider '{provider_name}'. Supported providers: 'imd', 'cwc', 'bbmb'.",
        )

    return await provider.check_health_async()


@router.post(
    "/probe",
    response_model=ProviderDashboardResponse,
    summary="Actively probe connectivity across all external telemetry providers",
)
async def probe_all_providers() -> ProviderDashboardResponse:
    """Trigger an active health and connectivity probe for all configured external providers."""
    return await check_all_providers_health_async()


@router.post(
    "/{provider_name}/probe",
    response_model=ProviderHealthStatus,
    summary="Actively probe health of a specific external telemetry provider",
)
async def probe_single_provider(provider_name: str) -> ProviderHealthStatus:
    """Trigger an active health and connectivity probe for a single external provider."""
    normalized = provider_name.strip().lower()
    if normalized == "imd":
        provider = IMDWeatherProvider()
    elif normalized == "cwc":
        provider = CWCRiverProvider()
    elif normalized == "bbmb":
        provider = BBMBDamProvider()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown telemetry provider '{provider_name}'. Supported providers: 'imd', 'cwc', 'bbmb'.",
        )

    return await provider.check_health_async()


