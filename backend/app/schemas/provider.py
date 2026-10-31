"""Provider connectivity and health validation schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field
from backend.app.schemas.common import BaseSchema


class NetworkStatus(str, Enum):
    """Accurate network connectivity state."""
    NOT_TESTED = "NOT_TESTED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONNECTED = "CONNECTED"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    TIMEOUT = "TIMEOUT"
    BLOCKED_BY_ACCESS = "BLOCKED_BY_ACCESS"


class ProviderStatus(str, Enum):
    """Categorized status for external hydrological and weather data providers."""
    CONFIGURED = "CONFIGURED"
    AUTHENTICATED = "AUTHENTICATED"
    CONNECTED = "CONNECTED"
    VALID_RESPONSE = "VALID_RESPONSE"
    LIVE_DATA_AVAILABLE = "LIVE_DATA_AVAILABLE"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    BLOCKED_BY_ACCESS = "BLOCKED_BY_ACCESS"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    DATA_INVALID = "DATA_INVALID"
    DATA_STALE = "DATA_STALE"


class ProviderHealthStatus(BaseSchema):
    """Detailed health, authentication, and live connectivity status of a provider."""
    provider_name: str = Field(..., description="Provider identifier (e.g. IMD, CWC, BBMB)")
    service_type: str = Field(..., description="Type of hydrological/meteorological service provided")
    status: ProviderStatus = Field(..., description="Current operational status")
    network_status: NetworkStatus = Field(
        NetworkStatus.NOT_TESTED,
        description="Accurate network connection state: NOT_TESTED, NOT_CONFIGURED, CONNECTED, CONNECTION_FAILED, TIMEOUT, BLOCKED_BY_ACCESS",
    )
    base_url: Optional[str] = Field(None, description="Configured base URL (sanitized)")
    verified_official_endpoint: str = Field(..., description="Official government portal or documentation endpoint")
    is_configured: bool = Field(False, description="Whether base URL is configured in settings")
    is_authenticated: bool = Field(False, description="Whether authentication was accepted by upstream")
    is_connected: bool = Field(False, description="Whether network connection succeeded")
    has_valid_response: bool = Field(False, description="Whether upstream returned a valid schema-compliant response")
    has_live_data: bool = Field(False, description="Whether actual live operational telemetry was retrieved")
    missing_credentials: List[str] = Field(default_factory=list, description="List of missing API keys or tokens")
    access_restriction: str = Field(..., description="Description of institutional access restrictions")
    last_successful_retrieval: Optional[datetime] = Field(None, description="UTC timestamp of last successful live payload")
    latest_data_timestamp: Optional[str] = Field(None, description="Observation timestamp of latest telemetry")
    last_probe_timestamp: Optional[datetime] = Field(None, description="UTC timestamp of last connectivity probe attempt")
    latency_ms: Optional[float] = Field(None, description="Round-trip response latency in milliseconds")
    error_message: Optional[str] = Field(None, description="Sanitized diagnostic message if an error occurred")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary diagnostic metadata")

    # Agent dependency and impact mapping
    dependent_agent_name: str = Field("Specialist Agent", description="Name of dependent specialist agent")
    impact_description: str = Field("", description="Operational impact when provider is unavailable")
    fallback_description: str = Field("", description="Fallback mechanism if provider is offline or unconfigured")
    data_freshness_status: str = Field("NOT_AVAILABLE", description="FRESH, DATA_STALE, or NOT_AVAILABLE")
    data_validation_status: str = Field("NOT_APPLICABLE", description="VALID, DATA_INVALID, or NOT_APPLICABLE")

    # Granular validation states (all 6 upstream gates must pass for operational availability)
    network_connectivity: str = Field(
        "NOT_TESTED",
        description="Network connectivity state: CONNECTED, CONNECTION_FAILED, TIMEOUT, NOT_CONFIGURED, NOT_TESTED",
    )
    authentication_status: str = Field(
        "NOT_APPLICABLE",
        description="Authentication state: AUTHENTICATED, ACCESS_DENIED, MISSING_CREDENTIALS, NOT_APPLICABLE",
    )
    payload_schema_validation: str = Field(
        "NOT_APPLICABLE",
        description="Payload schema state: VALID, INVALID_SCHEMA, NON_JSON_RESPONSE, NOT_APPLICABLE",
    )
    measurement_validation: str = Field(
        "NOT_APPLICABLE",
        description="Measurement validation state: VALID_MEASUREMENTS, MISSING_MEASUREMENTS, NOT_APPLICABLE",
    )
    timestamp_validation: str = Field(
        "NOT_APPLICABLE",
        description="Timestamp validation state: VALID_TIMESTAMP, MISSING_TIMESTAMP, INVALID_TIMESTAMP, NOT_APPLICABLE",
    )
    data_freshness: str = Field(
        "NOT_AVAILABLE",
        description="Data freshness state: FRESH, STALE, NOT_AVAILABLE",
    )
    operational_data_available: bool = Field(
        False,
        description="Operational live availability: True only when network, auth, schema, measurements, timestamp, and freshness all pass",
    )


class ProviderDashboardResponse(BaseSchema):
    """Aggregated status overview for all external flood data telemetry providers."""
    summary: Dict[str, Any] = Field(..., description="Summary counts and overall telemetry readiness")
    providers: Dict[str, ProviderHealthStatus] = Field(..., description="Per-provider health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
