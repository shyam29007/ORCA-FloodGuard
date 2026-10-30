"""Regression tests for SQLite database schema migration and persistence safety."""

import sqlite3
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.base import Base
from backend.app.database.models import FloodAssessment, Village, VillageRiskOutlook
from backend.app.database.migration import (
    migrate_sqlite_file,
    run_database_migrations,
    get_sqlite_table_columns,
)
from backend.app.services.assessment_service import AssessmentService
from backend.app.orchestrator.workflow import run_full_village_assessment
from backend.app.schemas.flood import RiskLevel


@pytest.fixture
def legacy_sqlite_db(tmp_path):
    """Create a temporary legacy SQLite database with NOT NULL on confidence_score and confidence."""
    db_file = tmp_path / "legacy_test.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()

    # Create villages table
    cur.execute("""
    CREATE TABLE villages (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        name_pa VARCHAR(100),
        district VARCHAR(100) NOT NULL,
        tehsil VARCHAR(100),
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        elevation_meters FLOAT,
        river_basin VARCHAR(100),
        nearest_river VARCHAR(100),
        distance_to_river_km FLOAT,
        is_flood_prone BOOLEAN,
        is_active BOOLEAN,
        created_at DATETIME,
        updated_at DATETIME
    );
    """)

    # Create older flood_assessments table with NOT NULL constraint on confidence_score
    cur.execute("""
    CREATE TABLE flood_assessments (
        id VARCHAR(36) PRIMARY KEY,
        run_id VARCHAR(64) NOT NULL,
        village_id VARCHAR(36) NOT NULL,
        overall_risk VARCHAR(30) NOT NULL,
        confidence_score FLOAT NOT NULL,
        validation_status VARCHAR(50) NOT NULL,
        triggered_rules_json JSON,
        explanation TEXT NOT NULL,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(village_id) REFERENCES villages (id) ON DELETE CASCADE
    );
    """)

    # Create older village_risk_outlooks table with NOT NULL constraint on confidence
    cur.execute("""
    CREATE TABLE village_risk_outlooks (
        id VARCHAR(36) PRIMARY KEY,
        assessment_id VARCHAR(36) NOT NULL,
        horizon VARCHAR(10) NOT NULL,
        risk_level VARCHAR(30) NOT NULL,
        confidence FLOAT NOT NULL,
        primary_factors_json JSON,
        triggered_rules_json JSON,
        rainfall_forecast_mm FLOAT,
        river_risk VARCHAR(30),
        dam_risk VARCHAR(30),
        created_at DATETIME,
        FOREIGN KEY(assessment_id) REFERENCES flood_assessments (id) ON DELETE CASCADE
    );
    """)

    # Insert sample village
    cur.execute("""
    INSERT INTO villages (id, name, district, latitude, longitude)
    VALUES ('vil-phil-01', 'Phillaur', 'Jalandhar', 31.0267, 75.7871);
    """)

    # Insert existing historical assessment record (with 0.9 confidence score from legacy run)
    cur.execute("""
    INSERT INTO flood_assessments (
        id, run_id, village_id, overall_risk, confidence_score, validation_status,
        triggered_rules_json, explanation, created_at, updated_at
    ) VALUES (
        'a953f9c6-5d20-4b0d-824c-5f97fb28a793',
        'run-87c592194cde',
        'vil-phil-01',
        'HIGH',
        0.9,
        'PASSED',
        '["RULE_HIGH_01_RIVER_ABOVE_WARNING"]',
        'Historical assessment for Phillaur before migration',
        '2026-10-30 10:00:00',
        '2026-10-30 10:00:00'
    );
    """)

    cur.execute("""
    INSERT INTO village_risk_outlooks (
        id, assessment_id, horizon, risk_level, confidence, created_at
    ) VALUES (
        'vo-phil-24h',
        'a953f9c6-5d20-4b0d-824c-5f97fb28a793',
        '24h',
        'HIGH',
        0.9,
        '2026-10-30 10:00:00'
    );
    """)

    conn.commit()
    conn.close()

    return str(db_file)


def test_migration_adds_confidence_status(legacy_sqlite_db):
    """1. Migration adds confidence_status and all new columns to flood_assessments."""
    # Before migration: verify confidence_status is missing
    conn = sqlite3.connect(legacy_sqlite_db)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(flood_assessments);")
    cols_before = [c[1] for c in cur.fetchall()]
    assert "confidence_status" not in cols_before
    conn.close()

    # Run migration
    applied = migrate_sqlite_file(legacy_sqlite_db)
    assert any("confidence_status" in s for s in applied)

    # After migration: verify confidence_status and other columns exist
    conn = sqlite3.connect(legacy_sqlite_db)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(flood_assessments);")
    cols_after = [c[1] for c in cur.fetchall()]
    assert "confidence_status" in cols_after
    assert "schema_validation_status" in cols_after
    assert "evidence_sufficiency_status" in cols_after
    assert "assessment_mode" in cols_after
    assert "assessment_status" in cols_after
    assert "limitations_json" in cols_after
    assert "warnings_json" in cols_after
    assert "excluded_evidence_json" in cols_after

    # Also verify village_risk_outlooks
    cur.execute("PRAGMA table_info(village_risk_outlooks);")
    outlook_cols = [c[1] for c in cur.fetchall()]
    assert "confidence_status" in outlook_cols
    assert "confidence_score" in outlook_cols
    assert "supporting_evidence_ids_json" in outlook_cols

    conn.close()


def test_database_accepts_null_in_confidence_score(legacy_sqlite_db):
    """2. Database accepts NULL in confidence_score and confidence after migration."""
    # Before migration: inserting NULL must fail due to NOT NULL constraint
    conn = sqlite3.connect(legacy_sqlite_db)
    cur = conn.cursor()
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("""
        INSERT INTO flood_assessments (
            id, run_id, village_id, overall_risk, confidence_score, validation_status, explanation
        ) VALUES ('fail-null', 'run-fail', 'vil-phil-01', 'LOW', NULL, 'PASSED', 'Should fail before migration');
        """)
    conn.close()

    # Apply migration
    migrate_sqlite_file(legacy_sqlite_db)

    # After migration: inserting NULL in confidence_score and confidence must succeed!
    conn = sqlite3.connect(legacy_sqlite_db)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO flood_assessments (
        id, run_id, village_id, overall_risk, confidence_score, validation_status, explanation
    ) VALUES ('succ-null', 'run-succ', 'vil-phil-01', 'LOW', NULL, 'PASSED', 'Should succeed after migration');
    """)
    cur.execute("""
    INSERT INTO village_risk_outlooks (
        id, assessment_id, horizon, risk_level, confidence
    ) VALUES ('succ-vo-null', 'succ-null', '24h', 'LOW', NULL);
    """)
    conn.commit()

    # Verify NULL is stored
    cur.execute("SELECT confidence_score FROM flood_assessments WHERE id = 'succ-null';")
    assert cur.fetchone()[0] is None

    cur.execute("SELECT confidence FROM village_risk_outlooks WHERE id = 'succ-vo-null';")
    assert cur.fetchone()[0] is None
    conn.close()


def test_migration_preserves_existing_assessment_records(legacy_sqlite_db):
    """3. Migration preserves all existing assessment records and populates safe defaults."""
    migrate_sqlite_file(legacy_sqlite_db)

    conn = sqlite3.connect(legacy_sqlite_db)
    cur = conn.cursor()
    cur.execute("""
    SELECT id, run_id, overall_risk, explanation, confidence_status, schema_validation_status, confidence_score
    FROM flood_assessments
    WHERE id = 'a953f9c6-5d20-4b0d-824c-5f97fb28a793';
    """)
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "a953f9c6-5d20-4b0d-824c-5f97fb28a793"
    assert row[1] == "run-87c592194cde"
    assert row[2] == "HIGH"
    assert "Historical assessment for Phillaur" in row[3]
    # New column defaults populated
    assert row[4] == "NOT_CALIBRATED"
    assert row[5] == "PASSED"
    # Existing 0.9 score preserved
    assert row[6] == 0.9

    # Verify outlook preserved
    cur.execute("SELECT id, confidence FROM village_risk_outlooks WHERE id = 'vo-phil-24h';")
    vo_row = cur.fetchone()
    assert vo_row is not None
    assert vo_row[1] == 0.9

    conn.close()


def test_running_migration_twice_is_safe(legacy_sqlite_db):
    """4. Running migration twice is idempotent and does not fail or duplicate columns."""
    applied_first = migrate_sqlite_file(legacy_sqlite_db)
    assert len(applied_first) > 0

    applied_second = migrate_sqlite_file(legacy_sqlite_db)
    assert len(applied_second) == 0

    # Record count remains identical
    conn = sqlite3.connect(legacy_sqlite_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM flood_assessments;")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_not_calibrated_assessment_saves_confidence_score_none(legacy_sqlite_db):
    """5. NOT_CALIBRATED assessment saves confidence_score=None without substituting 0."""
    engine = create_engine(f"sqlite:///{legacy_sqlite_db}")
    Base.metadata.create_all(bind=engine)
    run_database_migrations(engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        resp = run_full_village_assessment(
            village_name="Phillaur",
            latitude=31.0267,
            longitude=75.7871,
            forecast_horizon_hours=72,
            operational_mode=False,
            db=db,
        )
        assert resp.confidence_status == "NOT_CALIBRATED"
        assert resp.confidence_score is None

        # Verify in database: must be None, NOT 0 or 0.0!
        saved = db.query(FloodAssessment).filter_by(id=resp.assessment_id).first()
        assert saved is not None
        assert saved.confidence_status == "NOT_CALIBRATED"
        assert saved.confidence_score is None

        # Verify outlooks in database also have confidence=None and confidence_score=None
        assert len(saved.outlooks) > 0
        for out in saved.outlooks:
            assert out.confidence_status == "NOT_CALIBRATED"
            assert out.confidence_score is None
            assert out.confidence is None
    finally:
        db.close()


def test_calibrated_confidence_values_can_still_be_stored(legacy_sqlite_db):
    """6. When a calibrated confidence value is provided, it is stored accurately and not discarded."""
    engine = create_engine(f"sqlite:///{legacy_sqlite_db}")
    Base.metadata.create_all(bind=engine)
    run_database_migrations(engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        service = AssessmentService(db)
        calibrated_state = {
            "run_id": f"run-{uuid.uuid4().hex[:8]}",
            "village": {
                "name": "Phillaur",
                "district": "Jalandhar",
                "latitude": 31.0267,
                "longitude": 75.7871,
            },
            "overall_risk": RiskLevel.HIGH,
            "confidence_status": "CALIBRATED_HYDROLOGIC_V1",
            "confidence_score": 0.88,
            "schema_validation_status": "PASSED",
            "evidence_sufficiency_status": "SUFFICIENT_LIVE",
            "assessment_mode": "OPERATIONAL",
            "assessment_status": "OPERATIONAL",
            "outlooks": {
                "24h": {
                    "horizon": "24h",
                    "risk_level": "HIGH",
                    "confidence_status": "CALIBRATED_HYDROLOGIC_V1",
                    "confidence_score": 0.88,
                    "confidence": 0.88,
                    "rainfall_forecast_mm": 45.0,
                }
            },
            "evidence_pool": [],
            "explanation": "Calibrated assessment test",
            "triggered_rules": ["RULE_01"],
            "agent_traces": {},
        }
        resp = service.persist_orchestrator_results(calibrated_state)
        assert resp.confidence_status == "CALIBRATED_HYDROLOGIC_V1"
        assert resp.confidence_score == 0.88

        # Verify persisted record
        saved = db.query(FloodAssessment).filter_by(id=resp.assessment_id).first()
        assert saved is not None
        assert saved.confidence_status == "CALIBRATED_HYDROLOGIC_V1"
        assert saved.confidence_score == 0.88

        # Verify retrieved via service
        retrieved = service.get_assessment(resp.assessment_id)
        assert retrieved is not None
        assert retrieved.confidence_score == 0.88
        assert retrieved.outlooks["24h"].confidence_score == 0.88
    finally:
        db.close()


def test_simulation_mode_remains_explicitly_labeled_simulation_demo(legacy_sqlite_db):
    """7. Simulation mode results are explicitly tagged SIMULATION_DEMO in DB and response."""
    engine = create_engine(f"sqlite:///{legacy_sqlite_db}")
    Base.metadata.create_all(bind=engine)
    run_database_migrations(engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        resp = run_full_village_assessment(
            village_name="Phillaur",
            latitude=31.0267,
            longitude=75.7871,
            operational_mode=False,
            db=db,
        )
        assert resp.assessment_mode == "SIMULATION_DEMO"
        assert resp.assessment_status == "SIMULATED_DEMO"
        assert "[SIMULATION DEMO]" in resp.explanation

        saved = db.query(FloodAssessment).filter_by(id=resp.assessment_id).first()
        assert saved is not None
        assert saved.assessment_mode == "SIMULATION_DEMO"
        assert saved.assessment_status == "SIMULATED_DEMO"
    finally:
        db.close()


def test_operational_mode_still_rejects_simulated_critical_evidence(legacy_sqlite_db):
    """8. Operational mode strictly rejects simulated critical evidence and flags INSUFFICIENT_EVIDENCE."""
    engine = create_engine(f"sqlite:///{legacy_sqlite_db}")
    Base.metadata.create_all(bind=engine)
    run_database_migrations(engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        resp = run_full_village_assessment(
            village_name="Phillaur",
            latitude=31.0267,
            longitude=75.7871,
            operational_mode=True,
            db=db,
        )
        assert resp.overall_risk == RiskLevel.INSUFFICIENT_EVIDENCE
        assert resp.evidence_sufficiency_status == "INSUFFICIENT_EVIDENCE"
        assert len(resp.excluded_evidence) > 0
    finally:
        db.close()
