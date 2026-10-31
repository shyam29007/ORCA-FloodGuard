"""Tests for accurate network diagnostics, decoupled connectivity states, and probe endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.provider import NetworkStatus, ProviderStatus
from backend.app.integrations import (
    IMDWeatherProvider,
    CWCRiverProvider,
    BBMBDamProvider,
)


def test_condition_1_no_base_url_reports_not_configured():
    """Condition 1: No base URL configured must yield NetworkStatus.NOT_CONFIGURED."""
    provider = IMDWeatherProvider(base_url=None, api_key=None)
    status = provider.check_health()
    assert status.network_status == NetworkStatus.NOT_CONFIGURED
    assert status.status == ProviderStatus.NOT_CONFIGURED
    assert status.is_connected is False
    assert status.last_probe_timestamp is not None


def test_condition_2_probe_never_executed_reports_not_tested():
    """Condition 2: Configured provider before any probe is executed must report NetworkStatus.NOT_TESTED."""
    provider = CWCRiverProvider(base_url="https://cwc.gov.in/telemetry", api_key="cwc-api-key")
    status = provider.get_untested_status()
    assert status.network_status == NetworkStatus.NOT_TESTED
    assert status.status == ProviderStatus.CONFIGURED
    assert status.is_connected is False
    assert status.last_probe_timestamp is None


def test_condition_3_successful_network_connection_reports_connected():
    """Condition 3: Successful network connection and valid response must report NetworkStatus.CONNECTED."""
    provider = IMDWeatherProvider(base_url="https://api.imd.gov.in", api_key="valid-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "district": "Jalandhar",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "rain_24h_mm": 24.5,
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        status = provider.check_health()
        assert status.network_status == NetworkStatus.CONNECTED
        assert status.status == ProviderStatus.LIVE_DATA_AVAILABLE
        assert status.is_connected is True
        assert status.has_valid_response is True
        assert status.last_probe_timestamp is not None


def test_condition_4_connection_refused_reports_connection_failed():
    """Condition 4: Network error / connection refused must report NetworkStatus.CONNECTION_FAILED."""
    provider = BBMBDamProvider(base_url="https://mock-bbmb.gov.in", api_key="bbmb-key")

    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        status = provider.check_health()
        assert status.network_status == NetworkStatus.CONNECTION_FAILED
        assert status.status == ProviderStatus.CONNECTION_FAILED
        assert status.is_connected is False
        assert status.last_probe_timestamp is not None
        assert "refused" in status.error_message.lower() or "connection" in status.error_message.lower()


def test_condition_5_timeout_reports_timeout():
    """Condition 5: Gateway probe timeout must report NetworkStatus.TIMEOUT."""
    provider = CWCRiverProvider(base_url="https://cwc.gov.in", api_key="cwc-key")

    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Request timed out after 5.0s")):
        status = provider.check_health()
        assert status.network_status == NetworkStatus.TIMEOUT
        assert status.status == ProviderStatus.CONNECTION_FAILED
        assert status.is_connected is False
        assert status.last_probe_timestamp is not None
        assert "timed out" in status.error_message.lower()


def test_condition_6_auth_failure_reports_connected_with_access_denied():
    """Condition 6: HTTP 401/403 means network connection succeeded but authorization failed."""
    provider = IMDWeatherProvider(base_url="https://api.imd.gov.in", api_key="expired-token")
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.Client.get", return_value=mock_resp):
        status = provider.check_health()
        # Explicit decoupling: network connection was established, but authentication was rejected
        assert status.network_status == NetworkStatus.CONNECTED
        assert status.status == ProviderStatus.ACCESS_DENIED
        assert status.is_connected is True
        assert status.is_authenticated is False
        assert status.has_live_data is False


def test_condition_7_invalid_payload_reports_connected_with_data_invalid():
    """Condition 7: HTTP 200 with non-JSON or invalid schema reports NetworkStatus.CONNECTED and DATA_INVALID."""
    provider = BBMBDamProvider(base_url="https://bbmb.gov.in", api_key="valid-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.json.side_effect = ValueError("Invalid JSON from upstream firewall")

    with patch("httpx.Client.get", return_value=mock_resp):
        status = provider.check_health()
        assert status.network_status == NetworkStatus.CONNECTED
        assert status.is_connected is True
        assert status.data_validation_status == "DATA_INVALID"
        assert status.has_valid_response is False
        assert status.has_live_data is False


def test_api_post_probe_all_endpoint():
    """POST /api/providers/probe invokes real probe on all gateways and returns aggregated status."""
    client = TestClient(app)
    resp = client.post("/api/providers/probe")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "providers" in data
    for prov in ("IMD", "CWC", "BBMB"):
        assert prov in data["providers"]
        assert "network_status" in data["providers"][prov]
        assert "last_probe_timestamp" in data["providers"][prov]
        # Never expose secrets
        assert "api_key" not in data["providers"][prov]


def test_api_post_probe_single_endpoint():
    """POST /api/providers/{name}/probe invokes probe for a designated gateway."""
    client = TestClient(app)
    for name in ("imd", "cwc", "bbmb"):
        resp = client.post(f"/api/providers/{name}/probe")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_name"].lower() == name
        assert "network_status" in data
        assert "last_probe_timestamp" in data

    # Invalid provider returns 404
    resp_invalid = client.post("/api/providers/nonexistent/probe")
    assert resp_invalid.status_code == 404

