"""Unit tests for evidence normalization, freshness, validation gate, and deterministic risk rules."""

from datetime import datetime, timezone, timedelta
from backend.app.schemas.evidence import (
    EvidenceRecordSchema,
    EvidenceStatus,
    EvidenceQuality,
    EvidenceCollectionSummary,
)
from backend.app.schemas.flood import RiskLevel
from backend.app.services.evidence_normalizer import EvidenceNormalizer
from backend.app.services.freshness_checker import FreshnessChecker
from backend.app.services.evidence_validator import EvidenceValidator
from backend.app.services.risk_assessment import DeterministicRiskEngine


def test_evidence_deduplication():
    now = datetime.now(timezone.utc)
    r1 = EvidenceRecordSchema(
        source="IMD",
        source_type="WEATHER_API",
        parameter="rainfall_24h",
        value=50.0,
        unit="mm",
        observed_at=now,
        status=EvidenceStatus.LIVE,
    )
    r2 = EvidenceRecordSchema(
        source="IMD",
        source_type="WEATHER_API",
        parameter="rainfall_24h",
        value=50.0,
        unit="mm",
        observed_at=now,
        status=EvidenceStatus.LIVE,
    )
    deduped = EvidenceNormalizer.deduplicate([r1, r2])
    assert len(deduped) == 1


def test_freshness_checker_flags_stale():
    now = datetime.now(timezone.utc)
    stale_time = now - timedelta(hours=36)
    r_stale = EvidenceRecordSchema(
        source="CWC",
        source_type="RIVER_GAUGE",
        parameter="river_water_level",
        value=213.5,
        unit="m",
        observed_at=stale_time,
        status=EvidenceStatus.LIVE,
    )
    evaluated = FreshnessChecker.evaluate_freshness([r_stale], max_age_hours=24)
    assert evaluated[0].status == EvidenceStatus.STALE
    assert any("stale" in f.lower() for f in evaluated[0].validation_flags)


def test_evidence_validator_detects_missing_critical():
    # Only supply rainfall, omit river water level
    now = datetime.now(timezone.utc)
    records = [
        EvidenceRecordSchema(
            source="IMD",
            source_type="WEATHER_API",
            parameter="rainfall_24h",
            value=45.0,
            unit="mm",
            observed_at=now,
            status=EvidenceStatus.LIVE,
        )
    ]
    is_valid, summary, contributing, excluded = EvidenceValidator.validate_collection(records)
    assert not is_valid
    assert "river_water_level" in summary.critical_missing


def test_risk_engine_returns_insufficient_evidence_when_invalid():
    summary = EvidenceCollectionSummary(
        total_records=1,
        is_valid_for_assessment=False,
        critical_missing=["river_water_level"],
        validation_messages=["Critical river stage telemetry missing"],
    )
    overall, outlooks, rules, explanation, mode, status, limitations = DeterministicRiskEngine.assess_village_risk(
        village_name="Gidderpindi",
        distance_to_river_km=1.2,
        is_low_lying=True,
        rainfall_24h_mm=0.0,
        rainfall_48h_mm=0.0,
        rainfall_72h_mm=0.0,
        river_above_warning=False,
        river_above_danger=False,
        river_buffer_to_danger=None,
        max_dam_discharge_cusecs=0.0,
        validation_summary=summary,
        contributing_evidence=[],
    )
    assert overall == RiskLevel.INSUFFICIENT_EVIDENCE
    assert outlooks["24h"].risk_level == RiskLevel.INSUFFICIENT_EVIDENCE
    assert "RULE_00_CRITICAL_EVIDENCE_MISSING" in rules


def test_risk_engine_critical_threshold():
    summary = EvidenceCollectionSummary(is_valid_for_assessment=True)
    overall, outlooks, rules, explanation, mode, status, limitations = DeterministicRiskEngine.assess_village_risk(
        village_name="Gidderpindi",
        distance_to_river_km=1.2,
        is_low_lying=True,
        rainfall_24h_mm=90.0,
        rainfall_48h_mm=160.0,
        rainfall_72h_mm=220.0,
        river_above_warning=True,
        river_above_danger=True,  # Breached danger level
        river_buffer_to_danger=-0.3,
        max_dam_discharge_cusecs=110000.0,  # Critical discharge
        validation_summary=summary,
        contributing_evidence=[],
    )
    assert overall == RiskLevel.CRITICAL
    assert outlooks["24h"].risk_level == RiskLevel.CRITICAL
    assert "RULE_CRIT_01_RIVER_ABOVE_DANGER" in rules
    assert "RULE_CRIT_02_DAM_CRITICAL_DISCHARGE" in rules


def test_risk_engine_low_threshold():
    summary = EvidenceCollectionSummary(is_valid_for_assessment=True)
    overall, outlooks, rules, explanation, mode, status, limitations = DeterministicRiskEngine.assess_village_risk(
        village_name="SafeVillage",
        distance_to_river_km=15.0,
        is_low_lying=False,
        rainfall_24h_mm=10.0,
        rainfall_48h_mm=15.0,
        rainfall_72h_mm=20.0,
        river_above_warning=False,
        river_above_danger=False,
        river_buffer_to_danger=3.5,
        max_dam_discharge_cusecs=15000.0,
        validation_summary=summary,
        contributing_evidence=[],
    )
    assert overall == RiskLevel.LOW
    assert outlooks["24h"].risk_level == RiskLevel.LOW
    assert "RULE_LOW_01_NORMAL_HYDROMETEOROLOGICAL_BASELINE" in rules

