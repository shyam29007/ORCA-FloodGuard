"""SQLAlchemy ORM models for all 12 domain entities."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Village(Base):
    """Monitored village in Punjab with geographic coordinates and flood risk metadata."""
    __tablename__ = "villages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name_pa: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Punjabi Gurmukhi script
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tehsil: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    river_basin: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nearest_river: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    distance_to_river_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_flood_prone: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    assessments: Mapped[List["FloodAssessment"]] = relationship("FloodAssessment", back_populates="village", cascade="all, delete-orphan")
    evacuation_routes: Mapped[List["EvacuationRoute"]] = relationship("EvacuationRoute", back_populates="origin_village", cascade="all, delete-orphan")
    resident_reports: Mapped[List["ResidentReport"]] = relationship("ResidentReport", back_populates="village")


class DataSource(Base):
    """External telemetry and forecast data sources."""
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # IMD, CWC, BBMB, NASA_SRTM, OSM
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # WEATHER_API, RIVER_GAUGE, DAM_TELEMETRY, GIS
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EvidenceRecord(Base):
    """Normalized evidence gathered by specialist agents."""
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("flood_assessments.id", ondelete="CASCADE"), nullable=True, index=True)
    village_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("villages.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    location_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    value_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_str: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    value_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # LIVE, HISTORICAL, SIMULATED, STALE, UNAVAILABLE
    quality: Mapped[str] = mapped_column(String(30), default="HIGH")
    limitations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_flags_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    assessment: Mapped[Optional["FloodAssessment"]] = relationship("FloodAssessment", back_populates="evidence_records")


class FloodAssessment(Base):
    """Complete multi-agent flood risk assessment for a village."""
    __tablename__ = "flood_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    village_id: Mapped[str] = mapped_column(String(36), ForeignKey("villages.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_risk: Mapped[str] = mapped_column(String(30), nullable=False)  # LOW, MODERATE, HIGH, CRITICAL, INSUFFICIENT_EVIDENCE
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    confidence_status: Mapped[str] = mapped_column(String(50), default="NOT_CALIBRATED")
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PASSED")
    schema_validation_status: Mapped[str] = mapped_column(String(50), default="PASSED")
    evidence_sufficiency_status: Mapped[str] = mapped_column(String(50), default="SUFFICIENT")
    assessment_mode: Mapped[str] = mapped_column(String(50), default="OPERATIONAL")
    assessment_status: Mapped[str] = mapped_column(String(50), default="OPERATIONAL")
    triggered_rules_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    limitations_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    warnings_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    excluded_evidence_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    village: Mapped["Village"] = relationship("Village", back_populates="assessments")
    outlooks: Mapped[List["VillageRiskOutlook"]] = relationship("VillageRiskOutlook", back_populates="assessment", cascade="all, delete-orphan")
    evidence_records: Mapped[List["EvidenceRecord"]] = relationship("EvidenceRecord", back_populates="assessment", cascade="all, delete-orphan")
    agent_executions: Mapped[List["AgentExecution"]] = relationship("AgentExecution", back_populates="assessment", cascade="all, delete-orphan")
    alert_drafts: Mapped[List["AlertDraft"]] = relationship("AlertDraft", back_populates="assessment", cascade="all, delete-orphan")


class VillageRiskOutlook(Base):
    """Forecast window specific risk outlook (24h, 48h, 72h)."""
    __tablename__ = "village_risk_outlooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("flood_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    horizon: Mapped[str] = mapped_column(String(10), nullable=False)  # 24h, 48h, 72h
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    confidence_status: Mapped[str] = mapped_column(String(50), default="NOT_CALIBRATED")
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    primary_factors_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    triggered_rules_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    supporting_evidence_ids_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    rainfall_forecast_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    river_risk: Mapped[str] = mapped_column(String(30), default="NORMAL")
    dam_risk: Mapped[str] = mapped_column(String(30), default="NORMAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    assessment: Mapped["FloodAssessment"] = relationship("FloodAssessment", back_populates="outlooks")


class AgentExecution(Base):
    """Detailed trace of an individual specialist agent execution."""
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assessment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("flood_assessments.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inputs_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    outputs_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    assessment: Mapped[Optional["FloodAssessment"]] = relationship("FloodAssessment", back_populates="agent_executions")


class ReliefCentre(Base):
    """Emergency shelter or relief facility."""
    __tablename__ = "relief_centres"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capacity_persons: Mapped[int] = mapped_column(Integer, default=500)
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    facilities_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    evacuation_routes: Mapped[List["EvacuationRoute"]] = relationship("EvacuationRoute", back_populates="relief_centre")


class EvacuationRoute(Base):
    """Corridor connecting a village to a safe relief shelter."""
    __tablename__ = "evacuation_routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_village_id: Mapped[str] = mapped_column(String(36), ForeignKey("villages.id", ondelete="CASCADE"), nullable=False, index=True)
    destination_relief_centre_id: Mapped[str] = mapped_column(String(36), ForeignKey("relief_centres.id", ondelete="CASCADE"), nullable=False, index=True)
    route_name: Mapped[str] = mapped_column(String(150), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CANDIDATE")  # VERIFIED_OPEN, CANDIDATE, UNVERIFIED, etc.
    elevation_profile_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    waypoints_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    known_hazards_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    origin_village: Mapped["Village"] = relationship("Village", back_populates="evacuation_routes")
    relief_centre: Mapped["ReliefCentre"] = relationship("ReliefCentre", back_populates="evacuation_routes")


class ResidentReport(Base):
    """Ground observation or flood report submitted by a resident."""
    __tablename__ = "resident_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    village_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("villages.id", ondelete="SET NULL"), nullable=True, index=True)
    village_name: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    water_level_inches: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observations: Mapped[str] = mapped_column(Text, nullable=False)
    reporter_name: Mapped[str] = mapped_column(String(100), default="Anonymous Citizen")
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING, VERIFIED, REJECTED, FLAGGED
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    village: Mapped[Optional["Village"]] = relationship("Village", back_populates="resident_reports")


class AlertDraft(Base):
    """Advisory draft generated for human review before dispatch."""
    __tablename__ = "alert_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("flood_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    village_id: Mapped[str] = mapped_column(String(36), ForeignKey("villages.id", ondelete="CASCADE"), nullable=False, index=True)
    village_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    english_text: Mapped[str] = mapped_column(Text, nullable=False)
    punjabi_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    target_channels_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_APPROVAL", index=True)  # DRAFT, PENDING_APPROVAL, APPROVED, REJECTED, DISPATCHED
    evidence_summary_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    assessment: Mapped["FloodAssessment"] = relationship("FloodAssessment", back_populates="alert_drafts")
    approvals: Mapped[List["AlertApproval"]] = relationship("AlertApproval", back_populates="alert_draft", cascade="all, delete-orphan")


class AlertApproval(Base):
    """Audit log of human approval or rejection of an alert draft."""
    __tablename__ = "alert_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id: Mapped[str] = mapped_column(String(36), ForeignKey("alert_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    approved_by: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # APPROVE, REJECT
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    dispatch_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    alert_draft: Mapped["AlertDraft"] = relationship("AlertDraft", back_populates="approvals")


class AuditLog(Base):
    """System-wide audit trail of operational actions."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    details_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
