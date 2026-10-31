"""Tests for shared provider infrastructure (BaseLiveDataProvider)."""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from backend.app.integrations.base import (
    BaseLiveDataProvider,
    ProviderAuthenticationException,
    ProviderConnectionException,
    ProviderResponseException,
    ProviderTimeoutException,
    mask_sensitive_headers,
)


def test_mask_sensitive_headers():
    """Verify credentials and keys are properly masked in headers."""
    raw = {
        "User-Agent": "ORCA-FloodGuard",
        "Authorization": "Bearer secret_jwt_token_12345",
        "X-API-KEY": "secret_api_key_67890",
        "Content-Type": "application/json",
    }
    masked = mask_sensitive_headers(raw)
    assert masked["User-Agent"] == "ORCA-FloodGuard"
    assert masked["Content-Type"] == "application/json"
    assert masked["Authorization"] == "***REDACTED***"
    assert masked["X-API-KEY"] == "***REDACTED***"


def test_provider_not_configured():
    """Provider without base_url raises ProviderConnectionException on request."""
    provider = BaseLiveDataProvider(provider_name="TestProvider", base_url=None)
    assert not provider.is_configured()
    with pytest.raises(ProviderConnectionException) as exc:
        provider.get("/test")
    assert "Base URL is not configured" in str(exc.value)


def test_auth_error_fails_immediately_without_retry():
    """HTTP 401/403 fails immediately without retrying."""
    provider = BaseLiveDataProvider(
        provider_name="TestProvider",
        base_url="https://mock.provider.gov.in",
        api_key="invalid_key",
        max_retries=3,
        backoff_factor=0.01,
    )

    mock_resp = MagicMock(status_code=401, text="Unauthorized: Invalid API Key")
    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        with pytest.raises(ProviderAuthenticationException) as exc:
            provider.get("/data")
        assert "Authentication failed (HTTP 401)" in str(exc.value)
        # Should NOT retry on authentication errors
        assert mock_get.call_count == 1


def test_transient_5xx_retries_and_succeeds():
    """Transient HTTP 500 error retries and succeeds on next attempt."""
    provider = BaseLiveDataProvider(
        provider_name="TestProvider",
        base_url="https://mock.provider.gov.in",
        max_retries=2,
        backoff_factor=0.01,
    )

    err_resp = MagicMock(status_code=503, text="Service Unavailable")
    ok_resp = MagicMock(status_code=200, json=lambda: {"status": "OK", "value": 42})

    with patch("httpx.Client.get", side_effect=[err_resp, ok_resp]) as mock_get:
        data = provider.get("/data")
        assert data["status"] == "OK"
        assert data["value"] == 42
        assert mock_get.call_count == 2
        assert provider.last_successful_retrieval is not None
        assert provider.last_error is None


def test_timeout_retry_exhaustion():
    """ConnectTimeout retries up to max_retries, then raises ProviderTimeoutException."""
    provider = BaseLiveDataProvider(
        provider_name="TestProvider",
        base_url="https://mock.provider.gov.in",
        max_retries=2,
        backoff_factor=0.01,
    )

    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Connection timed out")) as mock_get:
        with pytest.raises(ProviderTimeoutException) as exc:
            provider.get("/data")
        assert "Timeout after 2 retries" in str(exc.value)
        assert mock_get.call_count == 3  # initial + 2 retries


def test_invalid_json_raises_provider_response_exception():
    """HTTP 200 with malformed JSON raises ProviderResponseException."""
    provider = BaseLiveDataProvider(
        provider_name="TestProvider",
        base_url="https://mock.provider.gov.in",
    )

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")

    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(ProviderResponseException) as exc:
            provider.get("/data")
        assert "Invalid JSON response" in str(exc.value)

