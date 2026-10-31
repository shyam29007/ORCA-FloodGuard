"""Base client and infrastructure for live hydrological and meteorological data providers."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Mapping, Tuple, List
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import (
    ProviderException,
    ProviderTimeoutException,
)
from backend.app.schemas.provider import ProviderStatus, ProviderHealthStatus, NetworkStatus


class ProviderAuthenticationException(ProviderException):
    """Raised when an external data provider rejects authentication (401 / 403)."""
    pass


class ProviderConnectionException(ProviderException):
    """Raised when an external data provider cannot be reached after retries."""
    pass


class ProviderResponseException(ProviderException):
    """Raised when an external provider returns unparseable or schema-violating data."""
    pass


def mask_sensitive_headers(headers: Optional[Mapping[str, str]]) -> Dict[str, str]:
    """Sanitize headers to ensure tokens and keys never leak into logs or traces."""
    if not headers:
        return {}
    sensitive_keys = {"authorization", "x-api-key", "api-key", "token", "secret", "password"}
    masked = {}
    for k, v in headers.items():
        if k.lower() in sensitive_keys:
            masked[k] = "***REDACTED***"
        else:
            masked[k] = v
    return masked


class BaseLiveDataProvider:
    """Abstract base provider with resilient HTTP communication, bounded backoff, and audit tracking."""

    service_type: str = "Hydrological Telemetry"
    requires_authentication: bool = True
    verified_official_endpoint: str = "Official government portal"
    access_restriction: str = "Institutional access required"
    expected_credential_names: List[str] = []
    health_check_endpoint: str = "/health"
    health_check_params: Optional[Dict[str, Any]] = None
    dependent_agent_name: str = "Specialist Agent"
    impact_description: str = "Live telemetry unavailable."
    fallback_description: str = "Simulated fallback if DEMO mode is enabled; INSUFFICIENT_EVIDENCE if OPERATIONAL mode."

    def __init__(
        self,
        provider_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        max_backoff: Optional[float] = None,
    ):
        self.provider_name = provider_name
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.PROVIDER_MAX_RETRIES
        self.backoff_factor = backoff_factor if backoff_factor is not None else settings.PROVIDER_RETRY_BACKOFF_FACTOR
        self.max_backoff = max_backoff if max_backoff is not None else settings.PROVIDER_MAX_BACKOFF_SECONDS

        self.last_successful_retrieval: Optional[datetime] = None
        self.last_error: Optional[str] = None

    def is_configured(self) -> bool:
        """Check if provider base URL is configured."""
        return bool(self.base_url and self.base_url.strip())

    def _get_auth_headers(self) -> Dict[str, str]:
        """Subclasses can override to inject authenticated headers."""
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": f"ORCA-FloodGuard/1.0 ({self.provider_name})",
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate bounded exponential backoff delay."""
        return min(self.backoff_factor * (2 ** attempt), self.max_backoff)

    def _handle_http_error(self, status_code: int, response_text: str, url: str) -> None:
        """Classify and raise structured provider exceptions without leaking credentials."""
        safe_url = url.split("?")[0]
        if status_code in (401, 403):
            err_msg = f"[{self.provider_name}] Authentication failed (HTTP {status_code}) for {safe_url}"
            self.last_error = err_msg
            logger.error(err_msg)
            raise ProviderAuthenticationException(err_msg, details={"status_code": status_code, "url": safe_url})

        err_msg = f"[{self.provider_name}] Upstream error (HTTP {status_code}) for {safe_url}: {response_text[:150]}"
        self.last_error = err_msg
        logger.error(err_msg)
        raise ProviderResponseException(err_msg, details={"status_code": status_code, "url": safe_url})

    def _validate_health_payload(self, data: Dict[str, Any]) -> Tuple[bool, bool, Optional[str], Dict[str, Any]]:
        """Hook for subclasses to validate health response schema and detect presence of live telemetry.

        Returns: (has_valid_schema, has_live_data, latest_data_timestamp, details)
        """
        return True, False, None, {}

    def _build_health_status(
        self,
        status: ProviderStatus,
        network_status: NetworkStatus = NetworkStatus.NOT_TESTED,
        is_configured: bool = False,
        is_authenticated: bool = False,
        is_connected: bool = False,
        has_valid_response: bool = False,
        has_live_data: bool = False,
        missing_credentials: Optional[List[str]] = None,
        latency_ms: Optional[float] = None,
        latest_data_timestamp: Optional[str] = None,
        last_probe_timestamp: Optional[datetime] = None,
        data_freshness_status: str = "NOT_AVAILABLE",
        data_validation_status: str = "NOT_APPLICABLE",
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        # Separate granular validation states
        network_connectivity: Optional[str] = None,
        authentication_status: Optional[str] = None,
        payload_schema_validation: Optional[str] = None,
        measurement_validation: Optional[str] = None,
        timestamp_validation: Optional[str] = None,
        data_freshness: Optional[str] = None,
        operational_data_available: Optional[bool] = None,
    ) -> ProviderHealthStatus:
        """Construct ProviderHealthStatus with full agent dependency and telemetry integrity metadata."""
        # Derive defaults if granular states not explicitly provided
        net_conn = network_connectivity or network_status.value
        miss_creds = missing_credentials if missing_credentials is not None else list(self.expected_credential_names)
        if authentication_status:
            auth_st = authentication_status
        elif is_authenticated:
            auth_st = "AUTHENTICATED"
        elif status in (ProviderStatus.ACCESS_DENIED, ProviderStatus.AUTHENTICATION_FAILED):
            auth_st = "ACCESS_DENIED"
        elif status == ProviderStatus.BLOCKED_BY_ACCESS or (getattr(self, "requires_authentication", True) and not self.api_key):
            auth_st = "MISSING_CREDENTIALS"
        elif miss_creds and len(miss_creds) > 0:
            auth_st = "MISSING_CREDENTIALS"
        elif not getattr(self, "requires_authentication", True):
            auth_st = "NOT_APPLICABLE"
        else:
            auth_st = "MISSING_CREDENTIALS"

        if payload_schema_validation:
            schema_st = payload_schema_validation
        elif has_valid_response:
            schema_st = "VALID"
        elif error_message and ("not valid json" in error_message.lower() or "html" in error_message.lower()):
            schema_st = "NON_JSON_RESPONSE"
        elif is_connected and is_authenticated:
            schema_st = "INVALID_SCHEMA"
        else:
            schema_st = "NOT_APPLICABLE"

        if measurement_validation:
            meas_st = measurement_validation
        elif has_live_data:
            meas_st = "VALID_MEASUREMENTS"
        elif has_valid_response:
            meas_st = "MISSING_MEASUREMENTS"
        else:
            meas_st = "NOT_APPLICABLE"

        if timestamp_validation:
            time_st = timestamp_validation
        elif latest_data_timestamp:
            time_st = "VALID_TIMESTAMP"
        elif has_valid_response:
            time_st = "MISSING_TIMESTAMP"
        else:
            time_st = "NOT_APPLICABLE"

        if data_freshness:
            fresh_st = data_freshness
        elif data_freshness_status in ("FRESH", "DATA_STALE"):
            fresh_st = "FRESH" if data_freshness_status == "FRESH" else "STALE"
        else:
            fresh_st = "NOT_AVAILABLE"

        requires_auth = getattr(self, "requires_authentication", True)
        if requires_auth:
            auth_ok = (auth_st == "AUTHENTICATED")
        else:
            auth_ok = (auth_st in ("AUTHENTICATED", "NOT_APPLICABLE"))

        if operational_data_available is not None:
            op_avail = operational_data_available
        else:
            op_avail = bool(
                net_conn == "CONNECTED"
                and auth_ok
                and schema_st == "VALID"
                and meas_st == "VALID_MEASUREMENTS"
                and time_st == "VALID_TIMESTAMP"
                and fresh_st == "FRESH"
                and status == ProviderStatus.LIVE_DATA_AVAILABLE
            )

        return ProviderHealthStatus(
            provider_name=self.provider_name,
            service_type=self.service_type,
            status=status,
            network_status=network_status,
            base_url=self.base_url if is_configured else None,
            verified_official_endpoint=self.verified_official_endpoint,
            is_configured=is_configured,
            is_authenticated=is_authenticated,
            is_connected=is_connected,
            has_valid_response=has_valid_response,
            has_live_data=has_live_data,
            missing_credentials=missing_credentials if missing_credentials is not None else list(self.expected_credential_names),
            access_restriction=self.access_restriction,
            last_successful_retrieval=self.last_successful_retrieval,
            latest_data_timestamp=latest_data_timestamp,
            last_probe_timestamp=last_probe_timestamp,
            latency_ms=latency_ms,
            error_message=error_message,
            details=details or {},
            dependent_agent_name=getattr(self, "dependent_agent_name", "Specialist Agent"),
            impact_description=getattr(self, "impact_description", "Live telemetry unavailable."),
            fallback_description=getattr(self, "fallback_description", "Simulated fallback if DEMO mode is enabled; INSUFFICIENT_EVIDENCE if OPERATIONAL mode."),
            data_freshness_status=data_freshness_status,
            data_validation_status=data_validation_status,
            network_connectivity=net_conn,
            authentication_status=auth_st,
            payload_schema_validation=schema_st,
            measurement_validation=meas_st,
            timestamp_validation=time_st,
            data_freshness=fresh_st,
            operational_data_available=op_avail,
        )

    def get_untested_status(self) -> ProviderHealthStatus:
        """Return provider status descriptor before any active connectivity probe has been executed."""
        if not self.is_configured():
            return self._build_health_status(
                status=ProviderStatus.NOT_CONFIGURED,
                network_status=NetworkStatus.NOT_CONFIGURED,
                is_configured=False,
                is_connected=False,
                is_authenticated=False,
                last_probe_timestamp=None,
                data_freshness_status="NOT_AVAILABLE",
                data_validation_status="NOT_APPLICABLE",
                error_message=f"[{self.provider_name}] Base URL is not configured.",
                details={"reason": "Provider base URL is unset in environment.", "network_status": NetworkStatus.NOT_CONFIGURED.value},
            )
        req_auth = getattr(self, "requires_authentication", True)
        return self._build_health_status(
            status=ProviderStatus.CONFIGURED if (not req_auth or self.api_key) else ProviderStatus.BLOCKED_BY_ACCESS,
            network_status=NetworkStatus.NOT_TESTED,
            is_configured=True,
            is_connected=False,
            is_authenticated=False,
            last_probe_timestamp=None,
            data_freshness_status="NOT_AVAILABLE",
            data_validation_status="NOT_APPLICABLE",
            error_message=None if (not req_auth or self.api_key) else f"[{self.provider_name}] Endpoint configured but required institutional API credentials are missing.",
            details={"reason": "Probe has never been executed.", "network_status": NetworkStatus.NOT_TESTED.value},
        )

    def check_health(self) -> ProviderHealthStatus:
        """Perform a synchronous health and connectivity verification check."""
        start_time = time.time()
        probe_ts = datetime.now(timezone.utc)

        # 1. Check if configured
        if not self.is_configured():
            return self._build_health_status(
                status=ProviderStatus.NOT_CONFIGURED,
                network_status=NetworkStatus.NOT_CONFIGURED,
                is_configured=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                data_freshness_status="NOT_AVAILABLE",
                data_validation_status="NOT_APPLICABLE",
                error_message=f"[{self.provider_name}] Base URL is not configured.",
                details={"reason": "Provider base URL is unset in environment.", "access_status": ProviderStatus.BLOCKED_BY_ACCESS.value, "network_status": NetworkStatus.NOT_CONFIGURED.value},
            )

        # 2. Check credentials availability
        if getattr(self, "requires_authentication", True) and not self.api_key:
            return self._build_health_status(
                status=ProviderStatus.BLOCKED_BY_ACCESS,
                network_status=NetworkStatus.BLOCKED_BY_ACCESS,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                data_freshness_status="NOT_AVAILABLE",
                data_validation_status="NOT_APPLICABLE",
                error_message=f"[{self.provider_name}] Endpoint configured but required institutional API credentials are missing.",
                details={"reason": "Missing institutional credentials or authorization token", "access_status": ProviderStatus.BLOCKED_BY_ACCESS.value, "network_status": NetworkStatus.BLOCKED_BY_ACCESS.value},
            )

        # 3. Probe endpoint with bounded timeout
        url = f"{self.base_url}/{self.health_check_endpoint.lstrip('/')}"
        params = self.health_check_params
        req_headers = self._get_auth_headers()
        probe_timeout = min(float(self.timeout), 5.0)

        try:
            with httpx.Client(timeout=probe_timeout) as client:
                resp = client.get(url, params=params, headers=req_headers)
                latency = round((time.time() - start_time) * 1000, 2)

                if resp.status_code in (401, 403):
                    return self._build_health_status(
                        status=ProviderStatus.ACCESS_DENIED,
                        network_status=NetworkStatus.CONNECTED,
                        is_configured=True,
                        is_authenticated=False,
                        is_connected=True,
                        last_probe_timestamp=probe_ts,
                        missing_credentials=[],
                        latency_ms=latency,
                        error_message=f"Authentication rejected by upstream with HTTP {resp.status_code}.",
                        details={"status_code": resp.status_code, "network_status": NetworkStatus.CONNECTED.value},
                    )

                if resp.status_code != 200:
                    return self._build_health_status(
                        status=ProviderStatus.CONNECTION_FAILED,
                        network_status=NetworkStatus.CONNECTION_FAILED,
                        is_configured=True,
                        is_authenticated=False,
                        is_connected=False,
                        last_probe_timestamp=probe_ts,
                        missing_credentials=[],
                        latency_ms=latency,
                        error_message=f"Upstream returned HTTP {resp.status_code}.",
                        details={"status_code": resp.status_code, "network_status": NetworkStatus.CONNECTION_FAILED.value},
                    )

                # Validate JSON body
                try:
                    payload = resp.json()
                except Exception as json_err:
                    return self._build_health_status(
                        status=ProviderStatus.CONNECTED,
                        network_status=NetworkStatus.CONNECTED,
                        is_configured=True,
                        is_authenticated=True,
                        is_connected=True,
                        has_valid_response=False,
                        has_live_data=False,
                        last_probe_timestamp=probe_ts,
                        missing_credentials=[],
                        latency_ms=latency,
                        data_validation_status="DATA_INVALID",
                        network_connectivity="CONNECTED",
                        authentication_status="AUTHENTICATED",
                        payload_schema_validation="NON_JSON_RESPONSE",
                        measurement_validation="NOT_APPLICABLE",
                        timestamp_validation="NOT_APPLICABLE",
                        data_freshness="NOT_AVAILABLE",
                        operational_data_available=False,
                        error_message=f"HTTP 200 received but payload is not valid JSON: {str(json_err)}",
                        details={"content_type": resp.headers.get("content-type"), "network_status": NetworkStatus.CONNECTED.value},
                    )

                valid_schema, live_data, latest_ts, diag = self._validate_health_payload(payload)
                is_fresh = bool(diag.get("is_fresh", live_data))
                has_meas = bool(diag.get("has_measurements", live_data))

                if not valid_schema:
                    status = ProviderStatus.CONNECTED
                    val_status = "DATA_INVALID"
                    schema_st = "INVALID_SCHEMA"
                    meas_st = "NOT_APPLICABLE"
                    time_st = "NOT_APPLICABLE"
                    fresh_st = "NOT_AVAILABLE"
                    op_avail = False
                    err_msg = "Response payload did not conform to expected schema."
                else:
                    schema_st = "VALID"
                    val_status = "VALID"
                    meas_st = "VALID_MEASUREMENTS" if has_meas else "MISSING_MEASUREMENTS"
                    time_st = "VALID_TIMESTAMP" if latest_ts else "MISSING_TIMESTAMP"
                    fresh_st = "FRESH" if is_fresh else ("STALE" if latest_ts else "NOT_AVAILABLE")

                    requires_auth = getattr(self, "requires_authentication", True)
                    auth_ok = bool(self.api_key and self.is_configured()) if requires_auth else True

                    # LIVE_DATA_AVAILABLE strictly requires network, auth, schema, measurements, timestamp, and freshness
                    op_avail = bool(
                        valid_schema
                        and auth_ok
                        and meas_st == "VALID_MEASUREMENTS"
                        and time_st == "VALID_TIMESTAMP"
                        and fresh_st == "FRESH"
                    )

                    if op_avail:
                        status = ProviderStatus.LIVE_DATA_AVAILABLE
                        self.last_successful_retrieval = datetime.now(timezone.utc)
                        err_msg = None
                    else:
                        status = ProviderStatus.VALID_RESPONSE
                        if not has_meas:
                            err_msg = "Response schema valid but contains null or missing telemetry measurements."
                        elif not is_fresh:
                            err_msg = "Telemetry timestamp is stale (> 24h old)."
                        else:
                            err_msg = "Operational live telemetry unavailable."

                diag["network_status"] = NetworkStatus.CONNECTED.value
                return self._build_health_status(
                    status=status,
                    network_status=NetworkStatus.CONNECTED,
                    is_configured=True,
                    is_authenticated=True,
                    is_connected=True,
                    has_valid_response=valid_schema,
                    has_live_data=op_avail,
                    missing_credentials=[],
                    latest_data_timestamp=latest_ts,
                    last_probe_timestamp=probe_ts,
                    latency_ms=latency,
                    data_freshness_status="FRESH" if fresh_st == "FRESH" else ("DATA_STALE" if fresh_st == "STALE" else "NOT_AVAILABLE"),
                    data_validation_status=val_status,
                    network_connectivity="CONNECTED",
                    authentication_status="AUTHENTICATED",
                    payload_schema_validation=schema_st,
                    measurement_validation=meas_st,
                    timestamp_validation=time_st,
                    data_freshness=fresh_st,
                    operational_data_available=op_avail,
                    error_message=err_msg,
                    details=diag,
                )

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as timeout_err:
            latency = round((time.time() - start_time) * 1000, 2)
            return self._build_health_status(
                status=ProviderStatus.CONNECTION_FAILED,
                network_status=NetworkStatus.TIMEOUT,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                latency_ms=latency,
                error_message=f"Connection timed out: {str(timeout_err)}",
                details={"note": "Upstream firewall or gateway timed out. Institutional IP whitelisting may be required.", "network_status": NetworkStatus.TIMEOUT.value},
            )
        except (httpx.ConnectError, httpx.NetworkError) as net_err:
            latency = round((time.time() - start_time) * 1000, 2)
            return self._build_health_status(
                status=ProviderStatus.CONNECTION_FAILED,
                network_status=NetworkStatus.CONNECTION_FAILED,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                latency_ms=latency,
                error_message=f"Network error connecting to upstream: {str(net_err)}",
                details={"network_status": NetworkStatus.CONNECTION_FAILED.value},
            )
        except Exception as gen_err:
            latency = round((time.time() - start_time) * 1000, 2)
            return self._build_health_status(
                status=ProviderStatus.CONNECTION_FAILED,
                network_status=NetworkStatus.CONNECTION_FAILED,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                latency_ms=latency,
                error_message=f"Health probe error: {str(gen_err)}",
                details={"network_status": NetworkStatus.CONNECTION_FAILED.value},
            )

    async def check_health_async(self) -> ProviderHealthStatus:
        """Perform an asynchronous health and connectivity verification check."""
        start_time = time.time()
        probe_ts = datetime.now(timezone.utc)

        # 1. Check if configured
        if not self.is_configured():
            return self._build_health_status(
                status=ProviderStatus.NOT_CONFIGURED,
                network_status=NetworkStatus.NOT_CONFIGURED,
                is_configured=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                data_freshness_status="NOT_AVAILABLE",
                data_validation_status="NOT_APPLICABLE",
                error_message=f"[{self.provider_name}] Base URL is not configured.",
                details={"reason": "Provider base URL is unset in environment.", "access_status": ProviderStatus.BLOCKED_BY_ACCESS.value, "network_status": NetworkStatus.NOT_CONFIGURED.value},
            )

        # 2. Check credentials availability
        if getattr(self, "requires_authentication", True) and not self.api_key:
            return self._build_health_status(
                status=ProviderStatus.BLOCKED_BY_ACCESS,
                network_status=NetworkStatus.BLOCKED_BY_ACCESS,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                data_freshness_status="NOT_AVAILABLE",
                data_validation_status="NOT_APPLICABLE",
                error_message=f"[{self.provider_name}] Endpoint configured but required institutional API credentials are missing.",
                details={"reason": "Missing institutional credentials or authorization token", "access_status": ProviderStatus.BLOCKED_BY_ACCESS.value, "network_status": NetworkStatus.BLOCKED_BY_ACCESS.value},
            )

        # 3. Probe endpoint with bounded timeout
        url = f"{self.base_url}/{self.health_check_endpoint.lstrip('/')}"
        params = self.health_check_params
        req_headers = self._get_auth_headers()
        probe_timeout = min(float(self.timeout), 5.0)

        try:
            async with httpx.AsyncClient(timeout=probe_timeout) as client:
                resp = await client.get(url, params=params, headers=req_headers)
                latency = round((time.time() - start_time) * 1000, 2)

                if resp.status_code in (401, 403):
                    return self._build_health_status(
                        status=ProviderStatus.ACCESS_DENIED,
                        network_status=NetworkStatus.CONNECTED,
                        is_configured=True,
                        is_authenticated=False,
                        is_connected=True,
                        last_probe_timestamp=probe_ts,
                        missing_credentials=[],
                        latency_ms=latency,
                        error_message=f"Authentication rejected by upstream with HTTP {resp.status_code}.",
                        details={"status_code": resp.status_code, "network_status": NetworkStatus.CONNECTED.value},
                    )

                if resp.status_code != 200:
                    return self._build_health_status(
                        status=ProviderStatus.CONNECTION_FAILED,
                        network_status=NetworkStatus.CONNECTION_FAILED,
                        is_configured=True,
                        is_authenticated=False,
                        is_connected=False,
                        last_probe_timestamp=probe_ts,
                        missing_credentials=[],
                        latency_ms=latency,
                        error_message=f"Upstream returned HTTP {resp.status_code}.",
                        details={"status_code": resp.status_code, "network_status": NetworkStatus.CONNECTION_FAILED.value},
                    )

                # Validate JSON body
                try:
                    payload = resp.json()
                except Exception as json_err:
                    return self._build_health_status(
                        status=ProviderStatus.CONNECTED,
                        network_status=NetworkStatus.CONNECTED,
                        is_configured=True,
                        is_authenticated=True,
                        is_connected=True,
                        has_valid_response=False,
                        has_live_data=False,
                        last_probe_timestamp=probe_ts,
                        missing_credentials=[],
                        latency_ms=latency,
                        data_validation_status="DATA_INVALID",
                        network_connectivity="CONNECTED",
                        authentication_status="AUTHENTICATED",
                        payload_schema_validation="NON_JSON_RESPONSE",
                        measurement_validation="NOT_APPLICABLE",
                        timestamp_validation="NOT_APPLICABLE",
                        data_freshness="NOT_AVAILABLE",
                        operational_data_available=False,
                        error_message=f"HTTP 200 received but payload is not valid JSON: {str(json_err)}",
                        details={"content_type": resp.headers.get("content-type"), "network_status": NetworkStatus.CONNECTED.value},
                    )

                valid_schema, live_data, latest_ts, diag = self._validate_health_payload(payload)
                is_fresh = bool(diag.get("is_fresh", live_data))
                has_meas = bool(diag.get("has_measurements", live_data))

                if not valid_schema:
                    status = ProviderStatus.CONNECTED
                    val_status = "DATA_INVALID"
                    schema_st = "INVALID_SCHEMA"
                    meas_st = "NOT_APPLICABLE"
                    time_st = "NOT_APPLICABLE"
                    fresh_st = "NOT_AVAILABLE"
                    op_avail = False
                    err_msg = "Response payload did not conform to expected schema."
                else:
                    schema_st = "VALID"
                    val_status = "VALID"
                    meas_st = "VALID_MEASUREMENTS" if has_meas else "MISSING_MEASUREMENTS"
                    time_st = "VALID_TIMESTAMP" if latest_ts else "MISSING_TIMESTAMP"
                    fresh_st = "FRESH" if is_fresh else ("STALE" if latest_ts else "NOT_AVAILABLE")

                    requires_auth = getattr(self, "requires_authentication", True)
                    auth_ok = bool(self.api_key and self.is_configured()) if requires_auth else True

                    # LIVE_DATA_AVAILABLE strictly requires network, auth, schema, measurements, timestamp, and freshness
                    op_avail = bool(
                        valid_schema
                        and auth_ok
                        and meas_st == "VALID_MEASUREMENTS"
                        and time_st == "VALID_TIMESTAMP"
                        and fresh_st == "FRESH"
                    )

                    if op_avail:
                        status = ProviderStatus.LIVE_DATA_AVAILABLE
                        self.last_successful_retrieval = datetime.now(timezone.utc)
                        err_msg = None
                    else:
                        status = ProviderStatus.VALID_RESPONSE
                        if not has_meas:
                            err_msg = "Response schema valid but contains null or missing telemetry measurements."
                        elif not is_fresh:
                            err_msg = "Telemetry timestamp is stale (> 24h old)."
                        else:
                            err_msg = "Operational live telemetry unavailable."

                diag["network_status"] = NetworkStatus.CONNECTED.value
                return self._build_health_status(
                    status=status,
                    network_status=NetworkStatus.CONNECTED,
                    is_configured=True,
                    is_authenticated=True,
                    is_connected=True,
                    has_valid_response=valid_schema,
                    has_live_data=op_avail,
                    missing_credentials=[],
                    latest_data_timestamp=latest_ts,
                    last_probe_timestamp=probe_ts,
                    latency_ms=latency,
                    data_freshness_status="FRESH" if fresh_st == "FRESH" else ("DATA_STALE" if fresh_st == "STALE" else "NOT_AVAILABLE"),
                    data_validation_status=val_status,
                    network_connectivity="CONNECTED",
                    authentication_status="AUTHENTICATED",
                    payload_schema_validation=schema_st,
                    measurement_validation=meas_st,
                    timestamp_validation=time_st,
                    data_freshness=fresh_st,
                    operational_data_available=op_avail,
                    error_message=err_msg,
                    details=diag,
                )

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as timeout_err:
            latency = round((time.time() - start_time) * 1000, 2)
            return self._build_health_status(
                status=ProviderStatus.CONNECTION_FAILED,
                network_status=NetworkStatus.TIMEOUT,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                latency_ms=latency,
                error_message=f"Connection timed out: {str(timeout_err)}",
                details={"note": "Upstream firewall or gateway timed out. Institutional IP whitelisting may be required.", "network_status": NetworkStatus.TIMEOUT.value},
            )
        except (httpx.ConnectError, httpx.NetworkError) as net_err:
            latency = round((time.time() - start_time) * 1000, 2)
            return self._build_health_status(
                status=ProviderStatus.CONNECTION_FAILED,
                network_status=NetworkStatus.CONNECTION_FAILED,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                latency_ms=latency,
                error_message=f"Network error connecting to upstream: {str(net_err)}",
                details={"network_status": NetworkStatus.CONNECTION_FAILED.value},
            )
        except Exception as gen_err:
            latency = round((time.time() - start_time) * 1000, 2)
            return self._build_health_status(
                status=ProviderStatus.CONNECTION_FAILED,
                network_status=NetworkStatus.CONNECTION_FAILED,
                is_configured=True,
                is_authenticated=False,
                is_connected=False,
                last_probe_timestamp=probe_ts,
                latency_ms=latency,
                error_message=f"Health probe error: {str(gen_err)}",
                details={"network_status": NetworkStatus.CONNECTION_FAILED.value},
            )

    async def get_async(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Perform asynchronous GET request with bounded exponential backoff retry."""
        if not self.is_configured():
            raise ProviderConnectionException(f"[{self.provider_name}] Base URL is not configured.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req_headers = self._get_auth_headers()
        if headers:
            req_headers.update(headers)

        safe_url = url.split("?")[0]
        attempt = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                try:
                    logger.debug("[%s] Requesting %s (attempt %d/%d)", self.provider_name, safe_url, attempt + 1, self.max_retries + 1)
                    resp = await client.get(url, params=params, headers=req_headers)

                    if resp.status_code == 200:
                        try:
                            payload = resp.json()
                            self.last_successful_retrieval = datetime.now(timezone.utc)
                            self.last_error = None
                            return payload
                        except Exception as json_err:
                            err_msg = f"[{self.provider_name}] Invalid JSON response from {safe_url}: {str(json_err)}"
                            self.last_error = err_msg
                            logger.error(err_msg)
                            raise ProviderResponseException(err_msg, details={"url": safe_url})

                    # If authentication failure, fail immediately without retry
                    if resp.status_code in (401, 403):
                        self._handle_http_error(resp.status_code, resp.text, url)

                    # Transient server error (5xx)
                    if 500 <= resp.status_code < 600:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt)
                            logger.warning("[%s] HTTP %d from %s; retrying in %0.2fs...", self.provider_name, resp.status_code, safe_url, delay)
                            await asyncio.sleep(delay)
                            attempt += 1
                            continue
                        self._handle_http_error(resp.status_code, resp.text, url)

                    # Other client errors (4xx)
                    self._handle_http_error(resp.status_code, resp.text, url)

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as timeout_err:
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff(attempt)
                        logger.warning("[%s] Timeout accessing %s; retrying in %0.2fs...", self.provider_name, safe_url, delay)
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                    err_msg = f"[{self.provider_name}] Timeout after {self.max_retries} retries connecting to {safe_url}: {str(timeout_err)}"
                    self.last_error = err_msg
                    logger.error(err_msg)
                    raise ProviderTimeoutException(err_msg, details={"url": safe_url})

                except httpx.NetworkError as conn_err:
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff(attempt)
                        logger.warning("[%s] Network connection error on %s; retrying in %0.2fs...", self.provider_name, safe_url, delay)
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                    err_msg = f"[{self.provider_name}] Network error after {self.max_retries} retries connecting to {safe_url}: {str(conn_err)}"
                    self.last_error = err_msg
                    logger.error(err_msg)
                    raise ProviderConnectionException(err_msg, details={"url": safe_url})

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Perform synchronous GET request with bounded exponential backoff retry."""
        if not self.is_configured():
            raise ProviderConnectionException(f"[{self.provider_name}] Base URL is not configured.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req_headers = self._get_auth_headers()
        if headers:
            req_headers.update(headers)

        safe_url = url.split("?")[0]
        attempt = 0

        with httpx.Client(timeout=self.timeout) as client:
            while True:
                try:
                    logger.debug("[%s] Synchronously requesting %s (attempt %d/%d)", self.provider_name, safe_url, attempt + 1, self.max_retries + 1)
                    resp = client.get(url, params=params, headers=req_headers)

                    if resp.status_code == 200:
                        try:
                            payload = resp.json()
                            self.last_successful_retrieval = datetime.now(timezone.utc)
                            self.last_error = None
                            return payload
                        except Exception as json_err:
                            err_msg = f"[{self.provider_name}] Invalid JSON response from {safe_url}: {str(json_err)}"
                            self.last_error = err_msg
                            logger.error(err_msg)
                            raise ProviderResponseException(err_msg, details={"url": safe_url})

                    # If authentication failure, fail immediately without retry
                    if resp.status_code in (401, 403):
                        self._handle_http_error(resp.status_code, resp.text, url)

                    # Transient server error (5xx)
                    if 500 <= resp.status_code < 600:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt)
                            logger.warning("[%s] HTTP %d from %s; retrying in %0.2fs...", self.provider_name, resp.status_code, safe_url, delay)
                            time.sleep(delay)
                            attempt += 1
                            continue
                        self._handle_http_error(resp.status_code, resp.text, url)

                    # Other client errors (4xx)
                    self._handle_http_error(resp.status_code, resp.text, url)

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as timeout_err:
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff(attempt)
                        logger.warning("[%s] Timeout accessing %s; retrying in %0.2fs...", self.provider_name, safe_url, delay)
                        time.sleep(delay)
                        attempt += 1
                        continue
                    err_msg = f"[{self.provider_name}] Timeout after {self.max_retries} retries connecting to {safe_url}: {str(timeout_err)}"
                    self.last_error = err_msg
                    logger.error(err_msg)
                    raise ProviderTimeoutException(err_msg, details={"url": safe_url})

                except httpx.NetworkError as conn_err:
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff(attempt)
                        logger.warning("[%s] Network connection error on %s; retrying in %0.2fs...", self.provider_name, safe_url, delay)
                        time.sleep(delay)
                        attempt += 1
                        continue
                    err_msg = f"[{self.provider_name}] Network error after {self.max_retries} retries connecting to {safe_url}: {str(conn_err)}"
                    self.last_error = err_msg
                    logger.error(err_msg)
                    raise ProviderConnectionException(err_msg, details={"url": safe_url})
