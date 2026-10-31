"""Comprehensive regression tests verifying that HTTP 200 or 2xx never independently establishes LIVE_DATA_AVAILABLE.

Covers:
1. HTTP 200 with HTML / SSO portal payload
2. HTTP 200 with malformed / invalid JSON syntax
3. HTTP 200 with valid JSON but null / missing measurements
4. HTTP 200 with valid measurements but stale timestamp (> 24h)
5. HTTP 401 / 403 authentication failures
6. Verification of all 7 decoupled validation gates:
   - Network connectivity
   - Authentication status
   - Payload schema validation
   - Measurement validation
   - Timestamp validation
   - Data freshness
   - Operational data availability
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import httpx
import pytest

from backend.app.schemas.provider import ProviderStatus, ProviderHealthStatus, NetworkStatus
from backend.app.integrations import (
    IMDWeatherProvider,
    CWCRiverProvider,
    BBMBDamProvider,
)


def test_http_200_with_html_payload_never_establishes_live_data_available():
    """An endpoint returning HTTP 200 with an HTML login page must NOT be marked LIVE_DATA_AVAILABLE."""
    provider = IMDWeatherProvider(base_url="https://mock-imd.gov.in", api_key="imd-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html; charset=UTF-8"}
    mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status != ProviderStatus.LIVE_DATA_AVAILABLE
        assert health.has_live_data is False
        assert health.has_valid_response is False
        assert health.operational_data_available is False
        assert health.payload_schema_validation == "NON_JSON_RESPONSE"
        assert health.measurement_validation == "NOT_APPLICABLE"
        assert health.timestamp_validation == "NOT_APPLICABLE"
        assert health.data_freshness == "NOT_AVAILABLE"


def test_http_200_with_invalid_json_never_establishes_live_data_available():
    """An endpoint returning HTTP 200 with malformed JSON must NOT be marked LIVE_DATA_AVAILABLE."""
    provider = CWCRiverProvider(base_url="https://mock-cwc.gov.in", api_key="cwc-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.side_effect = ValueError("Unterminated string starting at line 1 column 12")

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status != ProviderStatus.LIVE_DATA_AVAILABLE
        assert health.has_live_data is False
        assert health.has_valid_response is False
        assert health.operational_data_available is False
        assert health.payload_schema_validation == "NON_JSON_RESPONSE"


def test_http_200_with_missing_measurements_never_establishes_live_data_available():
    """An endpoint returning valid schema but null/empty measurements must NOT be marked LIVE_DATA_AVAILABLE."""
    provider = BBMBDamProvider(base_url="https://mock-bbmb.gov.in", api_key="bbmb-test-key")

    fresh_ts = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA",
                "name": "Bhakra Dam",
                "water_level_m": None,
                "outflow_discharge_cusecs": None,
                "observed_at": fresh_ts,
            }
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status != ProviderStatus.LIVE_DATA_AVAILABLE
        assert health.status == ProviderStatus.VALID_RESPONSE
        assert health.has_live_data is False
        assert health.operational_data_available is False
        assert health.measurement_validation == "MISSING_MEASUREMENTS"
        assert health.timestamp_validation == "VALID_TIMESTAMP"


def test_http_200_with_stale_timestamp_never_establishes_live_data_available():
    """An endpoint returning valid measurements but a timestamp older than 24 hours must NOT be marked LIVE_DATA_AVAILABLE."""
    provider = IMDWeatherProvider(base_url="https://mock-imd.gov.in", api_key="imd-test-key")

    stale_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "district": "Jalandhar",
        "rain_24h_mm": 54.2,
        "observed_at": stale_ts,
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status != ProviderStatus.LIVE_DATA_AVAILABLE
        assert health.status == ProviderStatus.VALID_RESPONSE
        assert health.has_live_data is False
        assert health.operational_data_available is False
        assert health.measurement_validation == "VALID_MEASUREMENTS"
        assert health.timestamp_validation == "VALID_TIMESTAMP"
        assert health.data_freshness == "STALE"


def test_http_401_403_authentication_failure_never_establishes_live_data_available():
    """An endpoint rejecting authentication must NOT be marked LIVE_DATA_AVAILABLE."""
    provider = CWCRiverProvider(base_url="https://mock-cwc.gov.in", api_key="bad-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status == ProviderStatus.ACCESS_DENIED
        assert health.has_live_data is False
        assert health.operational_data_available is False
        assert health.network_connectivity == "CONNECTED"
        assert health.authentication_status == "ACCESS_DENIED"
        assert health.payload_schema_validation == "NOT_APPLICABLE"


def test_live_data_available_only_when_all_7_gates_pass():
    """LIVE_DATA_AVAILABLE strictly requires network, auth, schema, measurements, timestamp, and freshness to pass."""
    provider = CWCRiverProvider(base_url="https://mock-cwc.gov.in", api_key="valid-cwc-key")

    fresh_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "station_name": "Phillaur",
        "water_level_m": 235.12,
        "discharge_cusecs": 32000.0,
        "observed_at": fresh_ts,
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        health = provider.check_health()
        assert health.status == ProviderStatus.LIVE_DATA_AVAILABLE
        assert health.has_live_data is True
        assert health.operational_data_available is True
        assert health.network_connectivity == "CONNECTED"
        assert health.authentication_status == "AUTHENTICATED"
        assert health.payload_schema_validation == "VALID"
        assert health.measurement_validation == "VALID_MEASUREMENTS"
        assert health.timestamp_validation == "VALID_TIMESTAMP"
        assert health.data_freshness == "FRESH"


def test_authentication_gate_enforcement():
    """Verify that MISSING_CREDENTIALS or ACCESS_DENIED never qualify as live data, and NOT_APPLICABLE is only permitted for public providers."""
    # 1. Provider requiring credentials without key -> BLOCKED_BY_ACCESS / MISSING_CREDENTIALS -> cannot be live
    imd = IMDWeatherProvider(base_url="https://mock-imd.gov.in", api_key=None)
    health_imd = imd.check_health()
    assert health_imd.status != ProviderStatus.LIVE_DATA_AVAILABLE
    assert health_imd.has_live_data is False
    assert health_imd.operational_data_available is False
    assert health_imd.authentication_status in ("MISSING_CREDENTIALS", "ACCESS_DENIED")

    # 2. Provider with invalid key -> 401 -> ACCESS_DENIED -> cannot be live
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch("httpx.Client.get", return_value=mock_resp):
        cwc = CWCRiverProvider(base_url="https://mock-cwc.gov.in", api_key="invalid-key")
        health_cwc = cwc.check_health()
        assert health_cwc.status == ProviderStatus.ACCESS_DENIED
        assert health_cwc.authentication_status == "ACCESS_DENIED"
        assert health_cwc.has_live_data is False
        assert health_cwc.operational_data_available is False

    # 3. Explicitly public provider (requires_authentication=False)
    class PublicHydrologyProvider(CWCRiverProvider):
        requires_authentication = False

    fresh_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.json.return_value = {
        "station_name": "Public Station",
        "water_level_m": 220.5,
        "discharge_cusecs": 15000.0,
        "observed_at": fresh_ts,
    }
    with patch("httpx.Client.get", return_value=mock_ok):
        pub = PublicHydrologyProvider(base_url="https://public-hydrology.gov.in", api_key=None)
        health_pub = pub.check_health()
        assert health_pub.has_live_data is True
        assert health_pub.status == ProviderStatus.LIVE_DATA_AVAILABLE


