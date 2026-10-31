"""Comprehensive tests for Alert RBAC, Assessment Foreign Key Safety, Notification Mode, and Evidence Metadata Consistency."""

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.auth import create_access_token
from backend.app.core.config import settings
from backend.app.schemas.auth import UserRole
from backend.app.schemas.river import RiverReading
from backend.app.schemas.dam import DamInformation
from backend.app.schemas.weather import WeatherForecastData
from backend.app.schemas.evidence import EvidenceStatus
from backend.app.tools.notification_tool import dispatch_alert
from backend.app.schemas.alerts import AlertDraftSchema, AlertStatus, AlertChannel


@pytest.fixture
def auth_tokens(client):
    """Generate or retrieve tokens for CITIZEN, FIELD_OFFICER, OFFICIAL, and ADMIN."""
    # Official
    off_resp = client.post("/api/auth/login", json={"email": "official@orca.punjab.gov.in", "password": "Official@123"})
    off_token = off_resp.json()["access_token"]

    # Citizen
    cit_resp = client.post("/api/auth/login", json={"email": "citizen@orca.punjab.gov.in", "password": "Citizen@123"})
    cit_token = cit_resp.json()["access_token"]

    # Admin
    adm_resp = client.post("/api/auth/login", json={"email": "admin@orca.punjab.gov.in", "password": "Admin@123"})
    adm_token = adm_resp.json()["access_token"]

    # Field Officer
    field_resp = client.post("/api/auth/login", json={"email": "field_officer@orca.punjab.gov.in", "password": "FieldOfficer@123"})
    field_token = field_resp.json()["access_token"]

    return {
        "OFFICIAL": off_token,
        "CITIZEN": cit_token,
        "ADMIN": adm_token,
        "FIELD_OFFICER": field_token,
    }


@pytest.fixture
def test_assessment(client):
    """Create a verified test assessment in DB."""
    assess_res = client.post("/api/flood/assess", json={
        "village_name": "Phillaur",
        "forecast_horizon_hours": 24,
        "include_simulated_fallback": True,
        "operational_mode": False,
    })
    assert assess_res.status_code == 200
    return assess_res.json()["data"]["assessment_id"]


@pytest.fixture
def test_alert(client, test_assessment, auth_tokens):
    """Create a verified test alert draft linked to test assessment."""
    draft_res = client.post(
        f"/api/alerts/draft?assessment_id={test_assessment}&village_name=Phillaur&overall_risk=HIGH&rainfall_24h_mm=75.0"
    )
    assert draft_res.status_code == 201
    return draft_res.json()["data"]["alert_id"]


# ==============================================================================
# BUG 1 TESTS: Alert Approval RBAC Enforcement
# ==============================================================================

def test_unauthenticated_approval_denied(client, test_alert):
    """Unauthenticated approval request must be rejected with HTTP 401."""
    payload = {
        "alert_id": test_alert,
        "approved_by": "Anonymous Approver",
        "action": "APPROVE",
    }
    resp = client.post(f"/api/alerts/{test_alert}/approve", json=payload)
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("WWW-Authenticate", "")


def test_invalid_and_expired_jwt_approval_denied(client, test_alert):
    """Tampered and expired JWTs must be rejected with HTTP 401."""
    # Invalid token
    bad_headers = {"Authorization": "Bearer invalid.jwt.token"}
    payload = {"alert_id": test_alert, "approved_by": "Attacker", "action": "APPROVE"}
    resp_bad = client.post(f"/api/alerts/{test_alert}/approve", json=payload, headers=bad_headers)
    assert resp_bad.status_code == 401

    # Expired token
    expired_token = create_access_token(
        {"sub": "usr-test", "email": "official@orca.punjab.gov.in", "role": "OFFICIAL"},
        expires_delta=timedelta(seconds=-30),
    )
    exp_headers = {"Authorization": f"Bearer {expired_token}"}
    resp_exp = client.post(f"/api/alerts/{test_alert}/approve", json=payload, headers=exp_headers)
    assert resp_exp.status_code == 401


def test_citizen_approval_denied_with_403(client, test_alert, auth_tokens):
    """Citizen role must be rejected with HTTP 403 Forbidden."""
    headers = {"Authorization": f"Bearer {auth_tokens['CITIZEN']}"}
    payload = {
        "alert_id": test_alert,
        "approved_by": "Citizen Approver",
        "action": "APPROVE",
    }
    resp = client.post(f"/api/alerts/{test_alert}/approve", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_field_officer_approval_denied_with_403(client, test_alert, auth_tokens):
    """Field Officer role must be rejected with HTTP 403 Forbidden."""
    headers = {"Authorization": f"Bearer {auth_tokens['FIELD_OFFICER']}"}
    payload = {
        "alert_id": test_alert,
        "approved_by": "Field Officer Approver",
        "action": "APPROVE",
    }
    resp = client.post(f"/api/alerts/{test_alert}/approve", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_demo_account_approval_denied_with_403(client, test_alert):
    """Restricted DEMO evaluator role must be rejected with HTTP 403 Forbidden."""
    login_resp = client.post("/api/auth/login", json={"email": "demo@orca.punjab.gov.in", "password": "Demo@123"})
    assert login_resp.status_code == 200
    demo_token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {demo_token}"}
    payload = {
        "alert_id": test_alert,
        "approved_by": "Demo Evaluator",
        "action": "APPROVE",
    }
    resp = client.post(f"/api/alerts/{test_alert}/approve", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_official_approval_accepted(client, test_alert, auth_tokens):
    """Official role must be accepted with HTTP 200 and APPROVED status."""
    headers = {"Authorization": f"Bearer {auth_tokens['OFFICIAL']}"}
    payload = {
        "alert_id": test_alert,
        "approved_by": "Er. Harjit Kaur",
        "action": "APPROVE",
        "modification_notes": "Official broadcast verified.",
    }
    resp = client.post(f"/api/alerts/{test_alert}/approve", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["action_taken"] == "APPROVE"
    assert "OFFICIAL" in data["approved_by"]


def test_admin_approval_accepted(client, test_assessment, auth_tokens):
    """Admin role must be accepted with HTTP 200 and APPROVED status."""
    # Draft new alert for admin test
    draft_res = client.post(
        f"/api/alerts/draft?assessment_id={test_assessment}&village_name=Phillaur&overall_risk=CRITICAL&rainfall_24h_mm=120.0"
    )
    admin_alert_id = draft_res.json()["data"]["alert_id"]

    headers = {"Authorization": f"Bearer {auth_tokens['ADMIN']}"}
    payload = {
        "alert_id": admin_alert_id,
        "approved_by": "System Admin",
        "action": "APPROVE",
    }
    resp = client.post(f"/api/alerts/{admin_alert_id}/approve", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "APPROVED"
    assert "ADMIN" in data["approved_by"]


def test_official_rejection_operation(client, test_assessment, auth_tokens):
    """Official may reject an alert draft, updating its status to REJECTED."""
    draft_res = client.post(
        f"/api/alerts/draft?assessment_id={test_assessment}&village_name=Phillaur&overall_risk=LOW"
    )
    rej_alert_id = draft_res.json()["data"]["alert_id"]

    headers = {"Authorization": f"Bearer {auth_tokens['OFFICIAL']}"}
    payload = {
        "alert_id": rej_alert_id,
        "approved_by": "Er. Harjit Kaur",
        "action": "REJECT",
        "modification_notes": "Risk lowered following water stage stabilization.",
    }
    resp = client.post(f"/api/alerts/{rej_alert_id}/approve", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "REJECTED"
    assert data["action_taken"] == "REJECT"


# ==============================================================================
# BUG 2 TESTS: Standalone Alert Draft Foreign Key Safety
# ==============================================================================

def test_draft_missing_assessment_id_rejected_with_422(client):
    """POST /api/alerts/draft without assessment_id must return HTTP 422."""
    resp = client.post("/api/alerts/draft?village_name=Phillaur&overall_risk=HIGH")
    assert resp.status_code == 422


def test_draft_nonexistent_assessment_id_rejected_with_404(client):
    """POST /api/alerts/draft with nonexistent assessment_id must return HTTP 404."""
    nonexistent_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(f"/api/alerts/draft?assessment_id={nonexistent_id}&village_name=Phillaur&overall_risk=HIGH")
    assert resp.status_code == 404
    assert f"Assessment '{nonexistent_id}' not found" in resp.json()["detail"]


def test_draft_valid_assessment_persists_successfully(client, test_assessment):
    """POST /api/alerts/draft with valid assessment_id persists with real foreign keys."""
    resp = client.post(
        f"/api/alerts/draft?assessment_id={test_assessment}&village_name=Phillaur&overall_risk=HIGH&rainfall_24h_mm=68.5"
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["assessment_id"] == test_assessment
    assert data["status"] == "PENDING_APPROVAL"


# ==============================================================================
# BUG 3 TESTS: Notification Mode & Dispatch Safety
# ==============================================================================

def test_mock_notification_mode_never_makes_external_call():
    """In MOCK mode, dispatch_alert must return status MOCKED with 0 external recipients."""
    alert = AlertDraftSchema(
        alert_id="test-alert-mock",
        assessment_id="test-assess",
        village_id="vil-test",
        village_name="Phillaur",
        risk_level="HIGH",
        headline="Test Headline",
        english_text="Test English advisory.",
        punjabi_text="ਟੈਸਟ ਪੰਜਾਬੀ ਚੇਤਾਵਨੀ।",
        recommended_action="Evacuate.",
        target_channels=[AlertChannel.SMS, AlertChannel.VOICE_CALL],
        status=AlertStatus.APPROVED,
    )
    settings.NOTIFICATION_MODE = "MOCK"
    result = dispatch_alert(alert)

    assert result["notification_mode"] == "MOCK"
    assert result["status"] == "MOCKED"
    assert result["external_network_call_made"] is False
    assert result["dispatched_channels"]["SMS"]["status"] == "MOCKED"
    assert result["dispatched_channels"]["SMS"]["recipient_count"] == 0
    assert result["dispatched_channels"]["SMS"]["delivery_confirmation"] == "NONE_SIMULATION_ONLY"


def test_live_notification_mode_fails_safely_when_unconfigured():
    """In LIVE mode, if SMS gateway is unconfigured or not in production, fail safely."""
    alert = AlertDraftSchema(
        alert_id="test-alert-live",
        assessment_id="test-assess",
        village_id="vil-test",
        village_name="Phillaur",
        risk_level="HIGH",
        headline="Test Headline",
        english_text="Test English advisory.",
        punjabi_text="ਟੈਸਟ ਪੰਜਾਬੀ ਚੇਤਾਵਨੀ।",
        recommended_action="Evacuate.",
        target_channels=[AlertChannel.SMS],
        status=AlertStatus.APPROVED,
    )
    settings.NOTIFICATION_MODE = "LIVE"
    settings.SMS_GATEWAY_URL = None
    result = dispatch_alert(alert)

    assert result["status"] == "FAILED"
    assert "unconfigured" in result["error"].lower()

    # Reset to MOCK for subsequent tests
    settings.NOTIFICATION_MODE = "MOCK"


def test_unapproved_alert_cannot_be_dispatched():
    """Alerts with status PENDING_APPROVAL must raise ValueError if dispatch is attempted."""
    unapproved_alert = AlertDraftSchema(
        alert_id="test-alert-pending",
        assessment_id="test-assess",
        village_id="vil-test",
        village_name="Phillaur",
        risk_level="HIGH",
        headline="Test Headline",
        english_text="Test English advisory.",
        punjabi_text="ਟੈਸਟ ਪੰਜਾਬੀ ਚੇਤਾਵਨੀ।",
        recommended_action="Evacuate.",
        target_channels=[AlertChannel.SMS],
        status=AlertStatus.PENDING_APPROVAL,
    )
    with pytest.raises(ValueError) as exc:
        dispatch_alert(unapproved_alert)
    assert "Human approval is required" in str(exc.value)


# ==============================================================================
# BUG 4 TESTS: Simulated Evidence Metadata Consistency
# ==============================================================================

def test_river_reading_metadata_consistency():
    """SIMULATED river readings must enforce is_simulated=True; LIVE must enforce is_simulated=False."""
    # Simulated
    sim_reading = RiverReading(
        station_id="CWC_SUTLEJ_PHILLAUR",
        water_level_meters=235.2,
        status=EvidenceStatus.SIMULATED,
    )
    assert sim_reading.status == EvidenceStatus.SIMULATED
    assert sim_reading.is_simulated is True

    # Live
    live_reading = RiverReading(
        station_id="CWC_SUTLEJ_PHILLAUR",
        water_level_meters=234.5,
        status=EvidenceStatus.LIVE,
    )
    assert live_reading.status == EvidenceStatus.LIVE
    assert live_reading.is_simulated is False


def test_dam_information_metadata_consistency():
    """SIMULATED dam telemetry must enforce is_simulated=True; LIVE must enforce is_simulated=False."""
    # Simulated
    sim_dam = DamInformation(
        dam_id="BBMB_BHAKRA_DAM",
        name="Bhakra Dam",
        river="Sutlej",
        full_reservoir_level_meters=512.06,
        status=EvidenceStatus.SIMULATED,
    )
    assert sim_dam.status == EvidenceStatus.SIMULATED
    assert sim_dam.is_simulated is True

    # Live
    live_dam = DamInformation(
        dam_id="BBMB_BHAKRA_DAM",
        name="Bhakra Dam",
        river="Sutlej",
        full_reservoir_level_meters=512.06,
        status=EvidenceStatus.LIVE,
    )
    assert live_dam.status == EvidenceStatus.LIVE
    assert live_dam.is_simulated is False


def test_weather_forecast_metadata_consistency():
    """Weather forecast with simulated source must enforce is_simulated=True."""
    sim_weather = WeatherForecastData(
        forecast_source="IMD_SIMULATED",
        rainfall_24h_mm=45.0,
    )
    assert sim_weather.is_simulated is True

    live_weather = WeatherForecastData(
        forecast_source="IMD_WEATHER",
        rainfall_24h_mm=12.0,
    )
    assert live_weather.is_simulated is False

