"""Evidence validation gate verifying completeness, integrity, physical bounds, freshness, and operational sufficiency."""

from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from backend.app.schemas.evidence import (
    EvidenceRecordSchema,
    EvidenceStatus,
    EvidenceCollectionSummary,
    ExcludedEvidenceRecord,
)
from backend.app.services.freshness_checker import FreshnessChecker
from backend.app.services.evidence_normalizer import EvidenceNormalizer


class EvidenceValidator:
    """Rigorous gate keeper enforcing physical, temporal, and operational constraints."""

    # Physical engineering plausibility bounds
    BOUNDS = {
        "rainfall_24h": (0.0, 1000.0, "mm"),
        "rainfall_48h": (0.0, 1500.0, "mm"),
        "rainfall_72h": (0.0, 2000.0, "mm"),
        "river_water_level": (100.0, 800.0, "m"),
        "dam_spillway_outflow": (0.0, 1000000.0, "cusecs"),
        "ground_elevation_amsl": (50.0, 4000.0, "m_amsl"),
    }

    # Minimum parameters considered critical for an authoritative flood outlook
    CRITICAL_PARAMETERS = ["rainfall_24h", "river_water_level"]

    @classmethod
    def validate_collection(
        cls,
        records: List[EvidenceRecordSchema],
        allow_simulated: bool = True,
        operational_mode: bool = False,
    ) -> Tuple[bool, EvidenceCollectionSummary, List[EvidenceRecordSchema], List[ExcludedEvidenceRecord]]:
        """Validate evidence collection and determine operational sufficiency.

        Returns (is_valid, summary, contributing_records, excluded_records).
        """
        now = datetime.now(timezone.utc)

        # Step 1: Deduplicate
        unique_records = EvidenceNormalizer.deduplicate(records)

        # Step 2: Freshness check
        freshened_records = FreshnessChecker.evaluate_freshness(unique_records)

        summary = EvidenceCollectionSummary(total_records=len(freshened_records))
        contributing_records: List[EvidenceRecordSchema] = []
        excluded_records: List[ExcludedEvidenceRecord] = []
        present_parameters_operational = set()
        present_parameters_simulated = set()

        for rec in freshened_records:
            # Count statuses
            if rec.status == EvidenceStatus.LIVE:
                summary.live_count += 1
            elif rec.status == EvidenceStatus.SIMULATED:
                summary.simulated_count += 1
            elif rec.status == EvidenceStatus.STATIC_REFERENCE:
                summary.static_reference_count += 1
            elif rec.status == EvidenceStatus.STALE:
                summary.stale_count += 1
            elif rec.status == EvidenceStatus.UNAVAILABLE:
                summary.unavailable_count += 1

            # Check timestamp consistency
            obs_tz = rec.observed_at if rec.observed_at.tzinfo is not None else rec.observed_at.replace(tzinfo=timezone.utc)
            if rec.status != EvidenceStatus.STATIC_REFERENCE and obs_tz > (now + timedelta(minutes=15)):
                exclusion = ExcludedEvidenceRecord(
                    evidence_id=rec.evidence_id,
                    source=rec.source,
                    parameter=rec.parameter,
                    status=rec.status,
                    reason_for_exclusion=f"Future observation timestamp ({obs_tz.isoformat()}) rejected for physical observation.",
                    eligibility_reason="FUTURE_TIMESTAMP_REJECTED",
                    exclusion_reason="TEMPORAL_INCONSISTENCY",
                )
                excluded_records.append(exclusion)
                continue

            # Check forecast valid time ordering
            if rec.forecast_valid_time and rec.forecast_issue_time:
                issue_tz = rec.forecast_issue_time if rec.forecast_issue_time.tzinfo is not None else rec.forecast_issue_time.replace(tzinfo=timezone.utc)
                valid_tz = rec.forecast_valid_time if rec.forecast_valid_time.tzinfo is not None else rec.forecast_valid_time.replace(tzinfo=timezone.utc)
                if valid_tz < issue_tz:
                    exclusion = ExcludedEvidenceRecord(
                        evidence_id=rec.evidence_id,
                        source=rec.source,
                        parameter=rec.parameter,
                        status=rec.status,
                        reason_for_exclusion="forecast_valid_time cannot be earlier than forecast_issue_time.",
                        eligibility_reason="FORECAST_ORDERING_INVALID",
                        exclusion_reason="TEMPORAL_INCONSISTENCY",
                    )
                    excluded_records.append(exclusion)
                    continue

            # Check value presence
            if rec.value is None or rec.status in (EvidenceStatus.UNAVAILABLE, EvidenceStatus.STALE):
                exclusion = ExcludedEvidenceRecord(
                    evidence_id=rec.evidence_id,
                    source=rec.source,
                    parameter=rec.parameter,
                    status=rec.status,
                    reason_for_exclusion=f"Value missing or unusable with status '{rec.status.value}'.",
                    eligibility_reason=f"VALUE_MISSING_OR_UNUSABLE_{rec.status.value}",
                    exclusion_reason="INCOMPLETE_DATA",
                )
                excluded_records.append(exclusion)
                continue

            # Check physical bounds if numeric
            is_bound_violated = False
            if isinstance(rec.value, (int, float)) and rec.parameter in cls.BOUNDS:
                min_v, max_v, expected_unit = cls.BOUNDS[rec.parameter]
                if not (min_v <= float(rec.value) <= max_v):
                    is_bound_violated = True
                    rec.validation_flags.append(
                        f"Value {rec.value} {rec.unit} out of physical bounds [{min_v}, {max_v}]"
                    )
                if rec.unit != expected_unit:
                    rec.validation_flags.append(
                        f"Unexpected unit '{rec.unit}', expected '{expected_unit}'"
                    )

            if is_bound_violated:
                exclusion = ExcludedEvidenceRecord(
                    evidence_id=rec.evidence_id,
                    source=rec.source,
                    parameter=rec.parameter,
                    status=rec.status,
                    reason_for_exclusion=f"Value {rec.value} violates physical plausibility bounds.",
                    eligibility_reason="PHYSICAL_BOUNDS_VIOLATION",
                    exclusion_reason="PLAUSIBILITY_CHECK_FAILED",
                )
                excluded_records.append(exclusion)
                continue

            # Check operational vs simulated admissibility
            if operational_mode and rec.status == EvidenceStatus.SIMULATED:
                exclusion = ExcludedEvidenceRecord(
                    evidence_id=rec.evidence_id,
                    source=rec.source,
                    parameter=rec.parameter,
                    status=rec.status,
                    reason_for_exclusion="SIMULATED evidence is strictly excluded from operational flood assessment.",
                    eligibility_reason="SIMULATED_DATA_EXCLUDED_FROM_OPERATIONAL_MODE",
                    exclusion_reason="SIMULATED_EVIDENCE_FORBIDDEN",
                )
                excluded_records.append(exclusion)
                continue

            # Track usable parameters
            if rec.status == EvidenceStatus.LIVE:
                present_parameters_operational.add(rec.parameter)
                present_parameters_simulated.add(rec.parameter)
            elif rec.status in (EvidenceStatus.STATIC_REFERENCE, EvidenceStatus.HISTORICAL):
                present_parameters_operational.add(rec.parameter)
                present_parameters_simulated.add(rec.parameter)
            elif rec.status == EvidenceStatus.SIMULATED and allow_simulated:
                present_parameters_simulated.add(rec.parameter)

            contributing_records.append(rec)

        # Step 3: Determine critical sufficiency
        if operational_mode:
            missing_operational = [p for p in cls.CRITICAL_PARAMETERS if p not in present_parameters_operational]
            summary.critical_missing = missing_operational
            if missing_operational:
                summary.is_valid_for_assessment = False
                summary.sufficiency_status = "INSUFFICIENT_EVIDENCE"
                summary.validation_messages.append(
                    f"Operational assessment halted: Critical live telemetry missing for {', '.join(missing_operational)}."
                )
            else:
                summary.is_valid_for_assessment = True
                summary.sufficiency_status = "SUFFICIENT_LIVE"
        else:
            # Simulation / Demo mode
            missing_sim = [p for p in cls.CRITICAL_PARAMETERS if p not in present_parameters_simulated]
            summary.critical_missing = missing_sim
            if missing_sim:
                summary.is_valid_for_assessment = False
                summary.sufficiency_status = "INSUFFICIENT_EVIDENCE"
                summary.validation_messages.append(
                    f"Simulation halted: Missing parameters {', '.join(missing_sim)}."
                )
            else:
                summary.is_valid_for_assessment = True
                if summary.simulated_count > 0:
                    summary.sufficiency_status = "SIMULATED_ONLY"
                else:
                    summary.sufficiency_status = "SUFFICIENT_LIVE"

        summary.excluded_records = excluded_records
        return summary.is_valid_for_assessment, summary, contributing_records, excluded_records
