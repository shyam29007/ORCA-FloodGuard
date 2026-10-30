"""Unit tests for database models, repositories, and SQLite fallback."""

import uuid
from datetime import datetime, timezone
from backend.app.database.models import (
    Village,
    DataSource,
    EvidenceRecord,
    FloodAssessment,
    VillageRiskOutlook,
    AgentExecution,
    ReliefCentre,
    EvacuationRoute,
    ResidentReport,
    AlertDraft,
    AlertApproval,
    AuditLog,
)
from backend.app.database.repositories import (
    VillageRepository,
    AssessmentRepository,
    ResidentReportRepository,
    AlertRepository,
    ReliefCentreRepository,
)


def test_village_repository(db_session):
    repo = VillageRepository(db_session)
    v = Village(
        id=str(uuid.uuid4()),
        name="TestVillage",
        district="Ludhiana",
        latitude=30.9,
        longitude=75.8,
        elevation_meters=245.0,
        river_basin="Sutlej",
    )
    repo.create(v)

    fetched = repo.get_by_name("TestVillage")
    assert fetched is not None
    assert fetched.district == "Ludhiana"

    nearest = repo.find_nearest(30.91, 75.81)
    assert nearest is not None
    assert nearest.name == "TestVillage"


def test_assessment_and_outlooks(db_session):
    village_repo = VillageRepository(db_session)
    v = Village(
        id=str(uuid.uuid4()),
        name="Lohian",
        district="Jalandhar",
        latitude=31.1,
        longitude=75.2,
    )
    village_repo.create(v)

    assessment_repo = AssessmentRepository(db_session)
    fa = FloodAssessment(
        run_id="run-123",
        village_id=v.id,
        overall_risk="HIGH",
        confidence_score=0.92,
        explanation="Elevated river discharge combined with heavy rainfall.",
    )
    outlooks = [
        VillageRiskOutlook(
            horizon="24h",
            risk_level="HIGH",
            confidence=0.9,
            rainfall_forecast_mm=85.0,
        ),
        VillageRiskOutlook(
            horizon="48h",
            risk_level="CRITICAL",
            confidence=0.85,
            rainfall_forecast_mm=140.0,
        ),
    ]
    ev_records = [
        EvidenceRecord(
            source="IMD",
            source_type="WEATHER_API",
            parameter="rainfall_24h",
            value_num=85.0,
            unit="mm",
            observed_at=datetime.now(timezone.utc),
            status="LIVE",
        )
    ]

    saved = assessment_repo.create_assessment(fa, outlooks, ev_records)
    assert saved.id is not None

    fetched = assessment_repo.get_by_id(saved.id)
    assert fetched is not None
    assert len(fetched.outlooks) == 2
    assert len(fetched.evidence_records) == 1
    assert fetched.village.name == "Lohian"


def test_alert_draft_and_human_approval(db_session):
    village_repo = VillageRepository(db_session)
    v = village_repo.create(
        Village(id=str(uuid.uuid4()), name="AlertVil", district="Rupnagar", latitude=31.2, longitude=76.5)
    )
    fa_repo = AssessmentRepository(db_session)
    fa = fa_repo.create_assessment(
        FloodAssessment(run_id="r1", village_id=v.id, overall_risk="HIGH", explanation="Risk high"),
        [],
        [],
    )

    alert_repo = AlertRepository(db_session)
    draft = AlertDraft(
        assessment_id=fa.id,
        village_id=v.id,
        village_name=v.name,
        risk_level="HIGH",
        headline="High Flood Warning for AlertVil",
        english_text="Water levels rising rapidly.",
        punjabi_text="ਪਾਣੀ ਦਾ ਪੱਧਰ ਵੱਧ ਰਿਹਾ ਹੈ।",
        recommended_action="Evacuate low lying areas immediately.",
        target_channels_json=["SMS", "VOICE_CALL"],
        status="PENDING_APPROVAL",
    )
    saved_draft = alert_repo.create_draft(draft)
    assert saved_draft.status == "PENDING_APPROVAL"

    approved = alert_repo.record_approval(
        alert_id=saved_draft.id,
        approved_by="DC Office Rupnagar",
        action="APPROVE",
        notes="Verified by Tehsildar",
    )
    assert approved is not None
    assert approved.status == "APPROVED"
    assert approved.approved_by == "DC Office Rupnagar"
    assert len(approved.approvals) == 1

