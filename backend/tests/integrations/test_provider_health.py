"""Tests for external provider health checks, connectivity status, and dashboard API."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.provider import ProviderStatus, ProviderHealthStatus
from backend.app.integrations import (
    IMDWeatherProvider,
    CWCRiverProvider,
    BBMBDamProvider,
    check_all_providers_health,
    check_all_providers_health_async,
)


def test_unconfigured_providers_report_not_configured():
    """Providers with empty base URLs must report NOT_CONFIGURED without attempting network connections."""
    imd = IMDWeatherProvider(base_url=None, api_key=None)
    status_imd = imd.check_health()
    assert status_imd.status == ProviderStatus.NOT_CONFIGURED
    assert status_imd.is_configured is False
    assert status_imd.has_live_data is False
    assert status_imd.is_connected is False
    assert "IMD_API_KEY" in status_imd.missing_credentials

    cwc = CWCRiverProvider(base_url=None, api_key=None)
    status_cwc = cwc.check_health()
    assert status_cwc.status == ProviderStatus.NOT_CONFIGURED
    assert status_cwc.is_configured is False
    assert status_cwc.has_live_data is False
    assert status_cwc.is_connected is False
    assert "CWC_API_KEY" in status_cwc.missing_credentials

    bbmb = BBMBDamProvider(base_url=None, api_key=None)
    status_bbmb = bbmb.check_health()
    assert status_bbmb.status == ProviderStatus.NOT_CONFIGURED
    assert status_bbmb.is_configured is False
    assert status_bbmb.has_live_data is False
    assert status_bbmb.is_connected is False
    assert "BBMB_API_KEY" in status_bbmb.missing_credentials


def test_configured_without_credentials_reports_blocked_by_access():
    """Configured base URL without credentials must report BLOCKED_BY_ACCESS and not claim LIVE status."""
    imd = IMDWeatherProvider(base_url="https://api.imd.gov.in", api_key=None)
    status_imd = imd.check_health()
    assert status_imd.status == ProviderStatus.BLOCKED_BY_ACCESS
    assert status_imd.is_configured is True
    assert status_imd.is_authenticated is False
    assert status_imd.has_live_data is False
    assert "IMD_API_KEY" in status_imd.missing_credentials
    assert "institutional" in status_imd.access_restriction.lower()


def test_provider_health_authentication_failure():
    """Provider receiving 401 or 403 must report ACCESS_DENIED."""
    provider = IMDWeatherProvider(base_url="https://mock-imd.gov.in", api_key="invalid-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status == ProviderStatus.ACCESS_DENIED
        assert health.is_connected is True
        assert health.is_authenticated is False
        assert health.has_live_data is False


def test_provider_health_connection_timeout():
    """Provider timing out during connection probe must report CONNECTION_FAILED."""
    provider = CWCRiverProvider(base_url="https://mock-cwc.gov.in", api_key="cwc-test-key")

    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Connection timed out")):
        health = provider.check_health()
        assert health.status == ProviderStatus.CONNECTION_FAILED
        assert health.is_connected is False
        assert health.has_live_data is False
        assert "timed out" in health.error_message.lower()


def test_http_200_with_html_payload_is_not_marked_live():
    """An endpoint returning HTTP 200 with HTML or non-JSON cannot be marked LIVE."""
    provider = BBMBDamProvider(base_url="https://mock-bbmb.gov.in", api_key="bbmb-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.json.side_effect = ValueError("Invalid JSON")

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.is_connected is True
        assert health.has_valid_response is False
        assert health.has_live_data is False
        assert health.status != ProviderStatus.LIVE_DATA_AVAILABLE


def test_http_200_with_null_measurements_is_not_marked_live():
    """An endpoint returning valid schema but null measurements cannot be marked LIVE."""
    provider = IMDWeatherProvider(base_url="https://mock-imd.gov.in", api_key="imd-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "district": "Jalandhar",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "rain_24h_mm": None,
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.is_connected is True
        assert health.has_valid_response is True
        assert health.has_live_data is False
        assert health.status == ProviderStatus.VALID_RESPONSE


def test_http_200_with_stale_timestamp_is_not_marked_live():
    """An endpoint returning valid schema with measurements older than 24h cannot be marked LIVE."""
    provider = CWCRiverProvider(base_url="https://mock-cwc.gov.in", api_key="cwc-test-key")

    stale_ts = (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "station_name": "Phillaur",
        "water_level_m": 234.5,
        "observed_at": stale_ts,
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.is_connected is True
        assert health.has_valid_response is True
        assert health.has_live_data is False
        assert health.status == ProviderStatus.VALID_RESPONSE


def test_http_200_with_fresh_telemetry_reports_live_data_available():
    """An endpoint returning fresh measurements within 24h is verified as LIVE_DATA_AVAILABLE."""
    provider = BBMBDamProvider(base_url="https://mock-bbmb.gov.in", api_key="bbmb-test-key")

    fresh_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA",
                "name": "Bhakra Dam",
                "water_level_m": 512.0,
                "outflow_discharge_cusecs": 45000.0,
                "observed_at": fresh_ts,
            }
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.is_connected is True
        assert health.has_valid_response is True
        assert health.has_live_data is True
        assert health.status == ProviderStatus.LIVE_DATA_AVAILABLE
        assert health.latest_data_timestamp == fresh_ts


def test_check_all_providers_health_aggregates_statuses():
    """check_all_providers_health returns a complete summary of all providers."""
    dashboard = check_all_providers_health()
    assert "summary" in dashboard.model_dump()
    assert dashboard.summary["total_providers"] == 3
    assert "IMD" in dashboard.providers
    assert "CWC" in dashboard.providers
    assert "BBMB" in dashboard.providers


@pytest.mark.asyncio
async def test_check_all_providers_health_async_aggregates():
    """check_all_providers_health_async concurrently checks all providers."""
    dashboard = await check_all_providers_health_async()
    assert dashboard.summary["total_providers"] == 3
    assert set(dashboard.providers.keys()) == {"IMD", "CWC", "BBMB"}


def test_api_providers_status_endpoint():
    """GET /api/providers/status returns 200 with provider readiness and no leaked credentials."""
    client = TestClient(app)
    response = client.get("/api/providers/status")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "providers" in data
    assert "IMD" in data["providers"]
    assert "CWC" in data["providers"]
    assert "BBMB" in data["providers"]

    # Verify credentials never leak
    serialized = response.text
    assert "X-API-KEY" not in serialized
    assert "secret" not in serialized.lower()


def test_api_single_provider_health_endpoints():
    """GET /api/providers/{name}/health returns health check for supported providers."""
    client = TestClient(app)
    for name in ("imd", "cwc", "bbmb"):
        resp = client.get(f"/api/providers/{name}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_name"].lower() == name

    # Unknown provider returns 404
    resp_unknown = client.get("/api/providers/unknown_provider/health")
    assert resp_unknown.status_code == 404

