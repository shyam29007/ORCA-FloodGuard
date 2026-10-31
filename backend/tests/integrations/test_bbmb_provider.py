"""Tests for BBMBDamProvider."""

import pytest
from unittest.mock import patch

from backend.app.integrations.bbmb_provider import BBMBDamProvider
from backend.app.schemas.evidence import EvidenceStatus


def test_bbmb_provider_valid_payload():
    """Verify parsing valid BBMB dam reservoir telemetry."""
    provider = BBMBDamProvider(base_url="https://api.bbmb.gov.in/v1")

    mock_payload = {
        "timestamp": "2026-07-10T06:00:00Z",
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA_DAM",
                "name": "Bhakra Dam",
                "river": "Sutlej",
                "full_reservoir_level_m": 512.06,
                "water_level_m": 508.2,
                "capacity_pct": 89.0,
                "inflow_cusecs": 52000.0,
                "outflow_discharge_cusecs": 60000.0,
                "spillway_gates_open": 4,
            },
            {
                "dam_id": "BBMB_PONG_DAM",
                "name": "Pong Dam",
                "river": "Beas",
                "full_reservoir_level_m": 426.72,
                "water_level_m": 422.0,
                "outflow_discharge_cusecs": 30000.0,
            },
        ],
    }

    with patch.object(provider, "get", return_value=mock_payload):
        dams, evidence = provider.fetch_dam_telemetry(river_basin="Sutlej")

        # Basin filtering checks
        assert len(dams) == 1
        assert dams[0].dam_id == "BBMB_BHAKRA_DAM"
        assert dams[0].outflow_discharge_cusecs == 60000.0
        assert dams[0].is_high_discharge is True  # 60000 >= 50000
        assert dams[0].is_critical_discharge is False
        assert dams[0].status == EvidenceStatus.LIVE

        assert len(evidence) == 1
        assert evidence[0].value == 60000.0
        assert evidence[0].status == EvidenceStatus.LIVE


def test_bbmb_provider_feet_to_meters_conversion():
    """Verify reservoir water level in feet is properly converted to meters."""
    provider = BBMBDamProvider(base_url="https://api.bbmb.gov.in/v1")

    mock_payload = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA_DAM",
                "name": "Bhakra Dam",
                "river": "Sutlej",
                "water_level_ft": 1665.0,  # 1665 * 0.3048 = 507.49 m
                "outflow_discharge_cusecs": 40000.0,
            }
        ]
    }

    with patch.object(provider, "get", return_value=mock_payload):
        dams, evidence = provider.fetch_dam_telemetry(river_basin="Sutlej")
        assert dams[0].current_water_level_meters == 507.49


def test_bbmb_provider_missing_discharge_remains_none():
    """Verify missing outflow discharge remains None without fabricating default values."""
    provider = BBMBDamProvider(base_url="https://api.bbmb.gov.in/v1")

    mock_payload = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA_DAM",
                "name": "Bhakra Dam",
                "river": "Sutlej",
                "water_level_m": 505.0,
                "outflow_discharge_cusecs": None,
            }
        ]
    }

    with patch.object(provider, "get", return_value=mock_payload):
        dams, evidence = provider.fetch_dam_telemetry(river_basin="Sutlej")
        assert dams[0].outflow_discharge_cusecs is None
        assert dams[0].is_high_discharge is False
        assert dams[0].is_critical_discharge is False
        assert dams[0].status == EvidenceStatus.UNAVAILABLE

        assert evidence[0].value is None
        assert evidence[0].status == EvidenceStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_bbmb_provider_async():
    """Verify async fetch_dam_telemetry_async."""
    provider = BBMBDamProvider(base_url="https://api.bbmb.gov.in/v1")

    mock_payload = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA_DAM",
                "name": "Bhakra Dam",
                "river": "Sutlej",
                "outflow_discharge_cusecs": 35000.0,
            }
        ]
    }

    with patch.object(provider, "get_async", return_value=mock_payload):
        dams, evidence = await provider.fetch_dam_telemetry_async(river_basin="Sutlej")
        assert len(dams) == 1
        assert dams[0].outflow_discharge_cusecs == 35000.0

