"""Tests for provider fallback behaviors and operational vs simulation mode separation."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from backend.app.tools.weather_tool import fetch_weather_forecast
from backend.app.tools.river_tool import fetch_river_reading
from backend.app.tools.dam_tool import fetch_dam_telemetry
from backend.app.schemas.evidence import EvidenceStatus
from backend.app.integrations.base import ProviderTimeoutException
from backend.app.orchestrator.workflow import run_full_village_assessment
from backend.app.schemas.flood import RiskLevel


def test_weather_tool_fallback_on_provider_error():
    """When IMD provider encounters network error, fallback adheres strictly to allow_simulated flag."""
    # 1. Operational Mode (allow_simulated=False): Must produce UNAVAILABLE with None values
    with patch("backend.app.integrations.imd_provider.IMDWeatherProvider.is_configured", return_value=True):
        with patch("backend.app.integrations.imd_provider.IMDWeatherProvider.fetch_forecast", side_effect=ProviderTimeoutException("Timeout")):
            forecast, evidence = fetch_weather_forecast(31.1465, 75.1872, allow_simulated=False)
            assert forecast.rainfall_24h_mm is None
            assert forecast.is_simulated is False
            for ev in evidence:
                assert ev.status == EvidenceStatus.UNAVAILABLE
                assert ev.value is None

    # 2. Simulation Demo Mode (allow_simulated=True): Produces representative SIMULATED data
    with patch("backend.app.integrations.imd_provider.IMDWeatherProvider.is_configured", return_value=True):
        with patch("backend.app.integrations.imd_provider.IMDWeatherProvider.fetch_forecast", side_effect=ProviderTimeoutException("Timeout")):
            forecast, evidence = fetch_weather_forecast(31.1465, 75.1872, allow_simulated=True)
            assert forecast.rainfall_24h_mm is not None
            assert forecast.is_simulated is True
            for ev in evidence:
                assert ev.status == EvidenceStatus.SIMULATED


def test_river_tool_fallback_on_provider_error():
    """When CWC provider encounters network error, fallback adheres strictly to allow_simulated flag."""
    # 1. Operational Mode (allow_simulated=False)
    with patch("backend.app.integrations.cwc_provider.CWCRiverProvider.is_configured", return_value=True):
        with patch("backend.app.integrations.cwc_provider.CWCRiverProvider.fetch_station_reading", side_effect=ProviderTimeoutException("Timeout")):
            reading, evidence = fetch_river_reading("CWC_SUTLEJ_LOHIAN", allow_simulated=False)
            assert reading.water_level_meters is None
            assert reading.status == EvidenceStatus.UNAVAILABLE
            assert evidence[0].status == EvidenceStatus.UNAVAILABLE

    # 2. Simulation Demo Mode (allow_simulated=True)
    with patch("backend.app.integrations.cwc_provider.CWCRiverProvider.is_configured", return_value=True):
        with patch("backend.app.integrations.cwc_provider.CWCRiverProvider.fetch_station_reading", side_effect=ProviderTimeoutException("Timeout")):
            reading, evidence = fetch_river_reading("CWC_SUTLEJ_LOHIAN", allow_simulated=True)
            assert reading.water_level_meters is not None
            assert reading.status == EvidenceStatus.SIMULATED
            assert evidence[0].status == EvidenceStatus.SIMULATED


def test_dam_tool_fallback_on_provider_error():
    """When BBMB provider encounters network error, fallback adheres strictly to allow_simulated flag."""
    # 1. Operational Mode (allow_simulated=False)
    with patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.is_configured", return_value=True):
        with patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.fetch_dam_telemetry", side_effect=ProviderTimeoutException("Timeout")):
            dams, evidence = fetch_dam_telemetry("Sutlej", allow_simulated=False)
            for d in dams:
                assert d.outflow_discharge_cusecs is None
                assert d.status == EvidenceStatus.UNAVAILABLE
            for ev in evidence:
                assert ev.status == EvidenceStatus.UNAVAILABLE

    # 2. Simulation Demo Mode (allow_simulated=True)
    with patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.is_configured", return_value=True):
        with patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.fetch_dam_telemetry", side_effect=ProviderTimeoutException("Timeout")):
            dams, evidence = fetch_dam_telemetry("Sutlej", allow_simulated=True)
            assert len(dams) > 0
            assert dams[0].outflow_discharge_cusecs is not None
            assert dams[0].status == EvidenceStatus.SIMULATED


def test_end_to_end_assessment_with_live_fresh_telemetry():
    """End-to-end assessment with fresh live provider telemetry produces OPERATIONAL assessment."""
    now = datetime.now(timezone.utc)
    fresh_time = (now - timedelta(hours=1)).isoformat()

    mock_weather = {
        "rain_24h_mm": 80.0,
        "rain_48h_mm": 125.0,
        "rain_72h_mm": 170.0,
        "observed_at": fresh_time,
    }
    mock_river = {
        "station_id": "CWC_SUTLEJ_PHILLAUR",
        "water_level_m": 235.8,  # between warning (235.0) and danger (236.0)
        "discharge_cusecs": 58000.0,
        "trend": "RISING",
        "observed_at": fresh_time,
    }
    mock_dam = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA_DAM",
                "name": "Bhakra Dam",
                "river": "Sutlej",
                "outflow_discharge_cusecs": 55000.0,
                "observed_at": fresh_time,
            }
        ]
    }

    with patch("backend.app.integrations.imd_provider.IMDWeatherProvider.is_configured", return_value=True), \
         patch("backend.app.integrations.imd_provider.IMDWeatherProvider.get", return_value=mock_weather), \
         patch("backend.app.integrations.cwc_provider.CWCRiverProvider.is_configured", return_value=True), \
         patch("backend.app.integrations.cwc_provider.CWCRiverProvider.get", return_value=mock_river), \
         patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.is_configured", return_value=True), \
         patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.get", return_value=mock_dam):

        resp = run_full_village_assessment(
            village_name="Phillaur",
            latitude=31.0267,
            longitude=75.7871,
            forecast_horizon_hours=72,
            include_simulated_fallback=False,
            operational_mode=True,
        )

        assert resp.assessment_mode == "OPERATIONAL"
        assert resp.assessment_status == "OPERATIONAL"
        assert resp.overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert resp.evidence_sufficiency_status == "SUFFICIENT_LIVE"

        # Verify all telemetry is tagged LIVE
        live_records = [ev for ev in resp.contributing_evidence if ev.status == EvidenceStatus.LIVE]
        assert len(live_records) >= 3  # rainfall, river level, dam outflow


def test_stale_telemetry_rejected_in_operational_mode():
    """Telemetry older than 24h is flagged STALE by FreshnessChecker and rejected as INSUFFICIENT_EVIDENCE."""
    now = datetime.now(timezone.utc)
    stale_time = (now - timedelta(hours=36)).isoformat()  # 36 hours old

    mock_weather = {
        "rain_24h_mm": 80.0,
        "observed_at": stale_time,
    }
    mock_river = {
        "station_id": "CWC_SUTLEJ_PHILLAUR",
        "water_level_m": 235.8,
        "observed_at": stale_time,
    }
    mock_dam = {
        "dams": [
            {
                "dam_id": "BBMB_BHAKRA_DAM",
                "name": "Bhakra Dam",
                "river": "Sutlej",
                "outflow_discharge_cusecs": 55000.0,
                "observed_at": stale_time,
            }
        ]
    }

    with patch("backend.app.integrations.imd_provider.IMDWeatherProvider.is_configured", return_value=True), \
         patch("backend.app.integrations.imd_provider.IMDWeatherProvider.get", return_value=mock_weather), \
         patch("backend.app.integrations.cwc_provider.CWCRiverProvider.is_configured", return_value=True), \
         patch("backend.app.integrations.cwc_provider.CWCRiverProvider.get", return_value=mock_river), \
         patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.is_configured", return_value=True), \
         patch("backend.app.integrations.bbmb_provider.BBMBDamProvider.get", return_value=mock_dam):

        resp = run_full_village_assessment(
            village_name="Phillaur",
            latitude=31.0267,
            longitude=75.7871,
            forecast_horizon_hours=72,
            include_simulated_fallback=False,
            operational_mode=True,
        )

        assert resp.overall_risk == RiskLevel.INSUFFICIENT_EVIDENCE
        assert resp.evidence_sufficiency_status == "INSUFFICIENT_EVIDENCE"
