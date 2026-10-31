"""Hydrological and meteorological external provider integrations."""

import asyncio
from datetime import datetime, timezone
from typing import Dict

from backend.app.core.config import settings
from backend.app.schemas.provider import (
    ProviderStatus,
    ProviderHealthStatus,
    ProviderDashboardResponse,
)
from backend.app.integrations.base import (
    BaseLiveDataProvider,
    ProviderAuthenticationException,
    ProviderConnectionException,
    ProviderResponseException,
    mask_sensitive_headers,
)
from backend.app.integrations.imd_provider import IMDWeatherProvider
from backend.app.integrations.cwc_provider import CWCRiverProvider
from backend.app.integrations.bbmb_provider import BBMBDamProvider


def check_all_providers_health() -> ProviderDashboardResponse:
    """Synchronously verify health and connectivity across all external telemetry providers."""
    imd = IMDWeatherProvider().check_health()
    cwc = CWCRiverProvider().check_health()
    bbmb = BBMBDamProvider().check_health()

    providers: Dict[str, ProviderHealthStatus] = {
        "IMD": imd,
        "CWC": cwc,
        "BBMB": bbmb,
    }

    live_count = sum(1 for p in providers.values() if p.has_live_data)
    configured_count = sum(1 for p in providers.values() if p.is_configured)
    blocked_count = sum(
        1 for p in providers.values()
        if p.status in (ProviderStatus.BLOCKED_BY_ACCESS, ProviderStatus.NOT_CONFIGURED, ProviderStatus.ACCESS_DENIED)
    )

    summary = {
        "total_providers": len(providers),
        "live_data_available_count": live_count,
        "configured_count": configured_count,
        "blocked_or_unconfigured_count": blocked_count,
        "operational_mode": settings.APP_ENV,
        "overall_status": "OPERATIONAL_READY" if live_count == len(providers) else "SIMULATION_FALLBACK",
    }

    return ProviderDashboardResponse(
        summary=summary,
        providers=providers,
        timestamp=datetime.now(timezone.utc),
    )


async def check_all_providers_health_async() -> ProviderDashboardResponse:
    """Asynchronously verify health and connectivity across all external telemetry providers concurrently."""
    imd_task = IMDWeatherProvider().check_health_async()
    cwc_task = CWCRiverProvider().check_health_async()
    bbmb_task = BBMBDamProvider().check_health_async()

    imd, cwc, bbmb = await asyncio.gather(imd_task, cwc_task, bbmb_task)

    providers: Dict[str, ProviderHealthStatus] = {
        "IMD": imd,
        "CWC": cwc,
        "BBMB": bbmb,
    }

    live_count = sum(1 for p in providers.values() if p.has_live_data)
    configured_count = sum(1 for p in providers.values() if p.is_configured)
    blocked_count = sum(
        1 for p in providers.values()
        if p.status in (ProviderStatus.BLOCKED_BY_ACCESS, ProviderStatus.NOT_CONFIGURED, ProviderStatus.ACCESS_DENIED)
    )

    summary = {
        "total_providers": len(providers),
        "live_data_available_count": live_count,
        "configured_count": configured_count,
        "blocked_or_unconfigured_count": blocked_count,
        "operational_mode": settings.APP_ENV,
        "overall_status": "OPERATIONAL_READY" if live_count == len(providers) else "SIMULATION_FALLBACK",
    }

    return ProviderDashboardResponse(
        summary=summary,
        providers=providers,
        timestamp=datetime.now(timezone.utc),
    )


__all__ = [
    "BaseLiveDataProvider",
    "ProviderAuthenticationException",
    "ProviderConnectionException",
    "ProviderResponseException",
    "mask_sensitive_headers",
    "IMDWeatherProvider",
    "CWCRiverProvider",
    "BBMBDamProvider",
    "check_all_providers_health",
    "check_all_providers_health_async",
]
