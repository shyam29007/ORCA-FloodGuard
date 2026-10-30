"""Evidence freshness and obsolescence detection service."""

from datetime import datetime, timezone
from typing import List
from backend.app.core.config import settings
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus


class FreshnessChecker:
    """Evaluates observation timestamps against maximum acceptable latency."""

    @staticmethod
    def evaluate_freshness(
        records: List[EvidenceRecordSchema],
        max_age_hours: int = settings.FRESHNESS_MAX_HOURS,
    ) -> List[EvidenceRecordSchema]:
        """Flag records exceeding maximum age as STALE."""
        now = datetime.now(timezone.utc)
        evaluated: List[EvidenceRecordSchema] = []

        for rec in records:
            # Static reference datasets (e.g. NASA SRTM elevation, baseline maps) do not decay by hourly observation age.
            # Unavailable and simulated records are also exempt from hourly staleness degradation.
            if rec.status in (EvidenceStatus.UNAVAILABLE, EvidenceStatus.SIMULATED, EvidenceStatus.STATIC_REFERENCE):
                evaluated.append(rec)
                continue

            # Calculate age of observation
            observed = rec.observed_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)

            age_hours = (now - observed).total_seconds() / 3600.0

            if age_hours > max_age_hours:
                rec.status = EvidenceStatus.STALE
                rec.validation_flags.append(f"Observation is stale ({age_hours:.1f} hours old, max allowed is {max_age_hours}h)")

            evaluated.append(rec)

        return evaluated

