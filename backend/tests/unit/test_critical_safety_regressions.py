"""Critical regression tests verifying assessment safety, evidence sufficiency, and timestamp semantics."""

from datetime import datetime, timezone, timedelta
from backend.app.schemas.evidence import (
    EvidenceRecordSchema,
    EvidenceStatus,
    EvidenceQuality,
    EvidenceCollectionSummary,
)
from backend.app.schemas.evacuation import (
    RouteVerificationStatus,
    RouteInspectionEvidence,
    ReliefCentreSchema,
)
from backend.app.schemas.flood import RiskLevel
from backend.app.services.evidence_validator import EvidenceValidator
from backend.app.services.risk_assessment import DeterministicRiskEngine
from backend.app.tools.elevation_tool import fetch_elevation_profile
from backend.app.tools.routing_tool import generate_candidate_routes
from backend.app.tools.weather_tool import fetch_weather_forecast
from backend.app.orchestrator.workflow import run_full_village_assessment


def test_simulated_evidence_cannot_be_treated_as_live():
    """1. Simulated river and rainfall evidence cannot be treated as live."""
    now = datetime.now(timezone.utc)
    rec_sim = EvidenceRecordSchema(
        source="IMD_MONSOON_SYNTHETIC",
        source_type="WEATHER_API",
        parameter="rainfall_24h",
        value=65.0,
        unit="mm",
        observed_at=now,
        status=EvidenceStatus.SIMULATED,
    )
    assert rec_sim.status == EvidenceStatus.SIMULATED
    assert rec_sim.status != EvidenceStatus.LIVE

    # In operational mode, simulated evidence MUST be rejected and moved to excluded_records
    is_valid, summary, contributing, excluded = EvidenceValidator.validate_collection(
        [rec_sim],
        allow_simulated=False,
        operational_mode=True,
    )
    assert not is_valid
    assert len(excluded) == 1
    assert "SIMULATED" in excluded[0].reason_for_exclusion
    assert summary.sufficiency_status == "INSUFFICIENT_EVIDENCE"


def test_missing_critical_river_telemetry_produces_insufficient_evidence():
    """2. Missing critical river telemetry produces INSUFFICIENT_EVIDENCE in operational mode."""
    now = datetime.now(timezone.utc)
    # Only rainfall provided; river water level missing
    records = [
        EvidenceRecordSchema(
            source="IMD",
            source_type="WEATHER_API",
            parameter="rainfall_24h",
            value=85.0,
            unit="mm",
            observed_at=now,
            status=EvidenceStatus.LIVE,
        )
    ]
    is_valid, summary, contributing, excluded = EvidenceValidator.validate_collection(
        records,
        operational_mode=True,
    )
    assert not is_valid
    assert "river_water_level" in summary.critical_missing
    assert summary.sufficiency_status == "INSUFFICIENT_EVIDENCE"

    overall, outlooks, rules, explanation, mode, status, limitations = (
        DeterministicRiskEngine.assess_village_risk(
            village_name="Phillaur",
            distance_to_river_km=0.8,
            is_low_lying=False,
            rainfall_24h_mm=85.0,
            rainfall_48h_mm=130.0,
            rainfall_72h_mm=180.0,
            river_above_warning=False,
            river_above_danger=False,
            river_buffer_to_danger=None,
            max_dam_discharge_cusecs=0.0,
            validation_summary=summary,
            contributing_evidence=contributing,
            operational_mode=True,
        )
    )
    assert overall == RiskLevel.INSUFFICIENT_EVIDENCE
    assert outlooks["24h"].risk_level == RiskLevel.INSUFFICIENT_EVIDENCE
    assert status == "INSUFFICIENT_EVIDENCE"


def test_static_srtm_data_is_not_marked_live():
    """3. Static SRTM data is not marked LIVE."""
    elev, is_low, records, warning = fetch_elevation_profile(
        latitude=31.0267,
        longitude=75.7871,
        village_name="Phillaur",
    )
    assert len(records) == 1
    rec = records[0]
    assert rec.status == EvidenceStatus.STATIC_REFERENCE
    assert rec.status != EvidenceStatus.LIVE
    assert rec.dataset_name is not None
    assert rec.vertical_datum == "EGM96 Geoid / AMSL"
    assert rec.spatial_resolution == "1 arc-second (~30 meters)"
    assert rec.limitations is not None and "Static digital elevation model" in rec.limitations


def test_unsupported_confidence_scores_are_not_returned():
    """4. Unsupported confidence scores are not returned (null and marked NOT_CALIBRATED)."""
    summary = EvidenceCollectionSummary(is_valid_for_assessment=True)
    overall, outlooks, rules, explanation, mode, status, limitations = (
        DeterministicRiskEngine.assess_village_risk(
            village_name="Phillaur",
            distance_to_river_km=0.8,
            is_low_lying=False,
            rainfall_24h_mm=25.0,
            rainfall_48h_mm=40.0,
            rainfall_72h_mm=55.0,
            river_above_warning=False,
            river_above_danger=False,
            river_buffer_to_danger=2.0,
            max_dam_discharge_cusecs=20000.0,
            validation_summary=summary,
            contributing_evidence=[],
            operational_mode=False,
        )
    )
    # Check that confidence scores are null and marked NOT_CALIBRATED
    for h, outlook in outlooks.items():
        assert outlook.confidence_score is None
        assert outlook.confidence_status == "NOT_CALIBRATED"
    assert any("NOT_CALIBRATED" in lim for lim in limitations)


def test_elevation_discrepancies_generate_warnings():
    """5. Elevation discrepancies beyond tolerance generate explicit warnings without silent overwrite."""
    # Test with village registry 234m vs test coordinates giving a divergent elevation
    elev, is_low, records, warning = fetch_elevation_profile(
        latitude=31.0267,
        longitude=75.7871,
        village_name="Phillaur",
        registered_elevation=214.0,  # Deliberately divergent by 20m
    )
    assert warning is not None
    assert "Elevation discrepancy detected" in warning
    assert "exceeds" in warning
    assert "214.0m AMSL" in warning
    assert "234.0m AMSL" in warning
    # Raw measurement from SRTM is preserved as 234.0m
    assert records[0].value == 234.0


def test_generated_routes_remain_candidate_or_unverified():
    """6. Generated routes remain CANDIDATE or UNVERIFIED."""
    centres = [
        ReliefCentreSchema(
            relief_centre_id="rc-phillaur-civic",
            name="Phillaur Civic Shelter",
            district="Jalandhar",
            latitude=31.0350,
            longitude=75.7920,
            distance_km=3.2,
        )
    ]
    routes = generate_candidate_routes(
        origin_village_id="vil-phillaur-03",
        village_name="Phillaur",
        origin_lat=31.0267,
        origin_lon=75.7871,
        relief_centres=centres,
    )
    assert len(routes) == 1
    assert routes[0].verification_status == RouteVerificationStatus.CANDIDATE
    assert routes[0].verification_status != RouteVerificationStatus.VERIFIED_OPEN
    assert routes[0].verification_status != "VERIFIED_SAFE"


def test_only_authorized_inspection_can_verify_route():
    """7. Only authorized inspection evidence can verify a route as VERIFIED_OPEN."""
    centres = [
        ReliefCentreSchema(
            relief_centre_id="rc-phillaur-civic",
            name="Phillaur Civic Shelter",
            district="Jalandhar",
            latitude=31.0350,
            longitude=75.7920,
            distance_km=3.2,
        )
    ]
    route_id = "route-vil-phil-to-rc-phill"
    inspection = RouteInspectionEvidence(
        route_id=route_id,
        authorized_source="Punjab DDMA Field Inspection Team Alpha",
        inspection_timestamp=datetime.now(timezone.utc),
        current_status=RouteVerificationStatus.VERIFIED_OPEN,
        inspector_name_or_id="SDM Phillaur Engineering Wing",
        supporting_evidence=["Aerial drone visual scan clear", "Pavement dry with zero standing water"],
    )

    routes = generate_candidate_routes(
        origin_village_id="vil-phil",
        village_name="Phillaur",
        origin_lat=31.0267,
        origin_lon=75.7871,
        relief_centres=centres,
        inspection_records=[inspection],
    )
    assert routes[0].verification_status == RouteVerificationStatus.VERIFIED_OPEN
    assert routes[0].inspection is not None
    assert routes[0].inspection.authorized_source == "Punjab DDMA Field Inspection Team Alpha"


def test_forecast_valid_timestamps_are_distinct_from_observation_timestamps():
    """8. Forecast-valid timestamps are distinct from observation timestamps."""
    forecast, records = fetch_weather_forecast(31.0267, 75.7871, district="Jalandhar")
    now = datetime.now(timezone.utc)
    for rec in records:
        # Observation/issuance timestamp is around current time, not in future
        assert rec.observed_at <= now + timedelta(minutes=5)
        # Forecast valid time is strictly in the future
        assert rec.forecast_valid_time is not None
        assert rec.forecast_valid_time > rec.observed_at


def test_simulation_results_are_explicitly_labeled():
    """9. Simulation results are explicitly labeled as SIMULATED_DEMO."""
    resp = run_full_village_assessment(
        village_name="Phillaur",
        latitude=31.0267,
        longitude=75.7871,
        district="Jalandhar",
        forecast_horizon_hours=72,
        include_simulated_fallback=True,
        operational_mode=False,
    )
    assert resp.assessment_mode == "SIMULATION_DEMO"
    assert resp.assessment_status == "SIMULATED_DEMO"
    assert resp.evidence_sufficiency_status == "SIMULATED_ONLY"
    assert "[SIMULATION DEMO]" in resp.explanation
    if resp.alert_draft:
        assert "[DEMO]" in resp.alert_draft.headline
        assert "[SIMULATION SCENARIO" in resp.alert_draft.english_text


def test_phillaur_assessment_end_to_end_safety(db_session):
    """10. Phillaur end-to-end assessment verification."""
    # Run Phillaur in demonstration mode
    resp = run_full_village_assessment(
        village_name="Phillaur",
        latitude=31.0267,
        longitude=75.7871,
        district="Jalandhar",
        forecast_horizon_hours=72,
        include_simulated_fallback=True,
        operational_mode=False,
        db=db_session,
    )
    assert resp.village.name == "Phillaur"
    assert resp.village.elevation_meters == 234.0
    assert resp.schema_validation_status == "PASSED"
    assert resp.confidence_score is None
    assert resp.confidence_status == "NOT_CALIBRATED"
    # Verification that static elevation is labeled STATIC_REFERENCE
    srtm_records = [ev for ev in resp.contributing_evidence if ev.source == "NASA_SRTM"]
    assert len(srtm_records) > 0
    assert srtm_records[0].status == EvidenceStatus.STATIC_REFERENCE
    # Verification that candidate routes are CANDIDATE
    assert resp.evacuation is not None
    for route in resp.evacuation.evacuation_routes:
        assert route.verification_status in (RouteVerificationStatus.CANDIDATE, RouteVerificationStatus.UNVERIFIED)


def test_evidence_status_consistency_and_eligibility_reason():
    """11. NASA SRTM preserves STATIC_REFERENCE status and excluded records have separate eligibility reasons."""
    from backend.app.services.freshness_checker import FreshnessChecker
    from backend.app.schemas.evidence import ExcludedEvidenceRecord

    srtm_rec = EvidenceRecordSchema(
        source="NASA_SRTM",
        source_type="GIS_ELEVATION",
        parameter="ground_elevation_amsl",
        value=214.0,
        unit="m_amsl",
        observed_at=datetime(2000, 2, 11, 0, 0, tzinfo=timezone.utc),
        status=EvidenceStatus.STATIC_REFERENCE,
    )
    # 1. Freshness checker must NOT mark STATIC_REFERENCE as STALE
    evaluated = FreshnessChecker.evaluate_freshness([srtm_rec])
    assert evaluated[0].status == EvidenceStatus.STATIC_REFERENCE
    assert evaluated[0].status != EvidenceStatus.STALE

    # 2. Excluded simulated record preserves true status and provides separate eligibility reason
    sim_rec = EvidenceRecordSchema(
        source="IMD_MONSOON_SYNTHETIC",
        source_type="WEATHER_API",
        parameter="rainfall_24h",
        value=50.0,
        unit="mm",
        observed_at=datetime.now(timezone.utc),
        status=EvidenceStatus.SIMULATED,
    )
    is_valid, summary, contributing, excluded = EvidenceValidator.validate_collection(
        [srtm_rec, sim_rec],
        allow_simulated=False,
        operational_mode=True,
    )
    # SRTM is accepted as static reference context in contributing evidence
    assert any(ev.source == "NASA_SRTM" and ev.status == EvidenceStatus.STATIC_REFERENCE for ev in contributing)
    # Simulated record is excluded, preserving its true status and separate reason
    assert len(excluded) == 1
    ex = excluded[0]
    assert ex.status == EvidenceStatus.SIMULATED
    assert ex.eligibility_reason == "SIMULATED_DATA_EXCLUDED_FROM_OPERATIONAL_MODE"
    assert ex.exclusion_reason == "SIMULATED_EVIDENCE_FORBIDDEN"


def test_missing_rainfall_returns_null_forecast():
    """12. When rainfall evidence is UNAVAILABLE, rainfall_forecast_mm is None instead of 0.0."""
    summary = EvidenceCollectionSummary(is_valid_for_assessment=False, critical_missing=["rainfall_24h"])
    overall, outlooks, rules, explanation, mode, status, limitations = (
        DeterministicRiskEngine.assess_village_risk(
            village_name="Phillaur",
            distance_to_river_km=0.8,
            is_low_lying=False,
            rainfall_24h_mm=None,  # Missing rainfall
            rainfall_48h_mm=None,
            rainfall_72h_mm=None,
            river_above_warning=False,
            river_above_danger=False,
            river_buffer_to_danger=None,
            max_dam_discharge_cusecs=0.0,
            validation_summary=summary,
            contributing_evidence=[],
            operational_mode=True,
        )
    )
    for h, out in outlooks.items():
        # Must be None, NOT 0.0!
        assert out.rainfall_forecast_mm is None
        assert out.rainfall_forecast_mm != 0.0


def test_operational_mode_evaluates_insufficient_evidence_without_live_telemetry():
    """13. Operational assessments evaluate to INSUFFICIENT_EVIDENCE when live telemetry is unavailable."""
    resp = run_full_village_assessment(
        village_name="Phillaur",
        latitude=31.0267,
        longitude=75.7871,
        district="Jalandhar",
        forecast_horizon_hours=72,
        include_simulated_fallback=False,
        operational_mode=True,
    )
    assert resp.assessment_mode == "OPERATIONAL"
    assert resp.overall_risk == RiskLevel.INSUFFICIENT_EVIDENCE
    assert resp.assessment_status == "INSUFFICIENT_EVIDENCE"
    assert resp.evidence_sufficiency_status == "INSUFFICIENT_EVIDENCE"
    for h, out in resp.outlooks.items():
        assert out.risk_level == RiskLevel.INSUFFICIENT_EVIDENCE


def test_relief_centres_distinguish_reference_from_verified_live():
    """14. Relief centres distinguish registered reference records from verified live information."""
    from backend.app.tools.relief_centre_tool import find_nearest_relief_centres

    centres = find_nearest_relief_centres(31.0267, 75.7871, district="Jalandhar", limit=3)
    assert len(centres) > 0
    for rc in centres:
        assert rc.verification_status == "REGISTERED_REFERENCE"
        assert rc.is_live_verified is False
        # Do not imply live occupancy or live available capacity
        assert rc.current_occupancy is None
        assert rc.available_capacity is None


def test_alert_drafts_remain_pending_approval_never_auto_dispatched():
    """15. Alert drafts are strictly created as PENDING_APPROVAL and never automatically dispatched."""
    from backend.app.schemas.alerts import AlertStatus

    resp = run_full_village_assessment(
        village_name="Phillaur",
        latitude=31.0267,
        longitude=75.7871,
        district="Jalandhar",
        forecast_horizon_hours=72,
        include_simulated_fallback=True,
        operational_mode=False,
    )
    if resp.alert_draft:
        assert resp.alert_draft.status == AlertStatus.PENDING_APPROVAL
        assert resp.alert_draft.status != AlertStatus.DISPATCHED
        assert resp.alert_draft.status != AlertStatus.APPROVED


