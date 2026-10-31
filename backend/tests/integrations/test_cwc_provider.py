"""Tests for CWCRiverProvider."""

import pytest
from unittest.mock import patch

from backend.app.integrations.cwc_provider import CWCRiverProvider
from backend.app.schemas.river import RiverStation
from backend.app.schemas.evidence import EvidenceStatus


@pytest.fixture
def sample_station():
    return RiverStation(
        station_id="CWC_SUTLEJ_LOHIAN",
        station_name="Lohian Khas Gauge",
        river_name="Sutlej",
        district="Jalandhar",
        latitude=31.1465,
        longitude=75.1872,
        warning_level_meters=213.5,
        danger_level_meters=214.5,
        highest_flood_level_meters=215.2,
    )


def test_cwc_provider_valid_payload(sample_station):
    """Verify parsing valid CWC river gauge payload."""
    provider = CWCRiverProvider(base_url="https://api.cwc.gov.in/v1")

    mock_payload = {
        "station_id": "CWC_SUTLEJ_LOHIAN",
        "water_level_m": 214.0,
        "discharge_cusecs": 55000.0,
        "trend": "RISING",
        "observed_at": "2026-07-10T10:00:00Z",
    }

    with patch.object(provider, "get", return_value=mock_payload):
        reading, evidence = provider.fetch_station_reading(sample_station.station_id, sample_station)

        assert reading.water_level_meters == 214.0
        assert reading.discharge_cusecs == 55000.0
        assert reading.trend == "RISING"
        assert reading.is_above_warning is True  # 214.0 >= 213.5
        assert reading.is_above_danger is False   # 214.0 < 214.5
        assert reading.buffer_to_danger_meters == 0.5  # 214.5 - 214.0
        assert reading.status == EvidenceStatus.LIVE

        assert len(evidence) == 2  # Level and discharge records
        ev_lvl = next(e for e in evidence if e.parameter == "river_water_level")
        assert ev_lvl.value == 214.0
        assert ev_lvl.status == EvidenceStatus.LIVE


def test_cwc_provider_cumecs_to_cusecs_conversion(sample_station):
    """Verify discharge in cumecs is accurately converted to cusecs."""
    provider = CWCRiverProvider(base_url="https://api.cwc.gov.in/v1")

    mock_payload = {
        "station_id": "CWC_SUTLEJ_LOHIAN",
        "water_level_m": 213.0,
        "discharge_cumecs": 1000.0,  # 1000 cumecs = 35314.7 cusecs
    }

    with patch.object(provider, "get", return_value=mock_payload):
        reading, evidence = provider.fetch_station_reading(sample_station.station_id, sample_station)
        assert reading.discharge_cusecs == 35314.7


def test_cwc_provider_missing_water_level_remains_none(sample_station):
    """Verify missing water level remains None without fabricating buffer or warning."""
    provider = CWCRiverProvider(base_url="https://api.cwc.gov.in/v1")

    mock_payload = {
        "station_id": "CWC_SUTLEJ_LOHIAN",
        "water_level_m": None,
    }

    with patch.object(provider, "get", return_value=mock_payload):
        reading, evidence = provider.fetch_station_reading(sample_station.station_id, sample_station)

        assert reading.water_level_meters is None
        assert reading.is_above_warning is False
        assert reading.is_above_danger is False
        assert reading.buffer_to_danger_meters is None
        assert reading.status == EvidenceStatus.UNAVAILABLE

        ev = evidence[0]
        assert ev.value is None
        assert ev.status == EvidenceStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_cwc_provider_async(sample_station):
    """Verify async fetch_station_reading_async."""
    provider = CWCRiverProvider(base_url="https://api.cwc.gov.in/v1")

    mock_payload = {
        "station_id": "CWC_SUTLEJ_LOHIAN",
        "water_level_m": 213.2,
    }

    with patch.object(provider, "get_async", return_value=mock_payload):
        reading, evidence = await provider.fetch_station_reading_async(sample_station.station_id, sample_station)
        assert reading.water_level_meters == 213.2

