"""Tests for IMDWeatherProvider."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from backend.app.integrations.imd_provider import IMDWeatherProvider, parse_to_utc
from backend.app.schemas.evidence import EvidenceStatus


def test_parse_to_utc_handles_ist_offset():
    """Verify Indian Standard Time (+05:30) offset string normalizes to UTC."""
    ist_str = "2026-07-10T14:00:00+05:30"
    utc_dt = parse_to_utc(ist_str)
    assert utc_dt.tzinfo is not None
    # 14:00 IST is 08:30 UTC
    assert utc_dt.hour == 8
    assert utc_dt.minute == 30
    assert utc_dt.tzinfo == timezone.utc


def test_imd_provider_valid_payload():
    """Verify parsing of valid IMD weather payload with distinct forecast horizons."""
    provider = IMDWeatherProvider(base_url="https://api.imd.gov.in/v1", api_key="test_key")

    mock_payload = {
        "rain_24h_mm": 65.5,
        "rain_48h_mm": 110.0,
        "rain_72h_mm": 165.2,
        "prob": 80.0,
        "temp": 29.2,
        "wind_speed_kmh": 22.0,
        "observed_at": "2026-07-10T08:30:00+05:30",
        "valid_time_24h": "2026-07-11T08:30:00+05:30",
        "valid_time_48h": "2026-07-12T08:30:00+05:30",
        "valid_time_72h": "2026-07-13T08:30:00+05:30",
    }

    with patch.object(provider, "get", return_value=mock_payload):
        forecast, evidence = provider.fetch_forecast(latitude=31.1465, longitude=75.1872, district="Jalandhar")

        assert forecast.rainfall_24h_mm == 65.5
        assert forecast.rainfall_48h_mm == 110.0
        assert forecast.rainfall_72h_mm == 165.2
        assert forecast.is_simulated is False
        assert forecast.forecast_source == "IMD_LIVE"

        # Evidence records check
        assert len(evidence) == 3
        ev24 = next(e for e in evidence if e.parameter == "rainfall_24h")
        assert ev24.value == 65.5
        assert ev24.status == EvidenceStatus.LIVE
        assert ev24.observed_at.hour == 3  # 08:30 IST -> 03:00 UTC
        assert ev24.forecast_valid_time > ev24.observed_at


def test_imd_provider_missing_measurements_remain_none():
    """Verify missing rainfall fields remain None and are tagged UNAVAILABLE."""
    provider = IMDWeatherProvider(base_url="https://api.imd.gov.in/v1")

    mock_payload = {
        "rain_24h_mm": None,
        "rain_48h_mm": None,
        "rain_72h_mm": None,
        "prob": 50.0,
    }

    with patch.object(provider, "get", return_value=mock_payload):
        forecast, evidence = provider.fetch_forecast(latitude=31.1465, longitude=75.1872)

        # Must NOT convert missing to 0.0!
        assert forecast.rainfall_24h_mm is None
        assert forecast.rainfall_48h_mm is None
        assert forecast.rainfall_72h_mm is None

        for ev in evidence:
            assert ev.value is None
            assert ev.status == EvidenceStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_imd_provider_async():
    """Verify async fetch_forecast_async performs as expected."""
    provider = IMDWeatherProvider(base_url="https://api.imd.gov.in/v1")

    mock_payload = {
        "rain_24h_mm": 45.0,
        "rain_48h_mm": 70.0,
        "rain_72h_mm": 95.0,
    }

    with patch.object(provider, "get_async", return_value=mock_payload):
        forecast, evidence = await provider.fetch_forecast_async(latitude=31.0267, longitude=75.7871)
        assert forecast.rainfall_24h_mm == 45.0
        assert len(evidence) == 3

