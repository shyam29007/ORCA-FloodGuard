"""Evidence freshness and obsolescence detection service."""

from datetime import datetime, timezone
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus


class FreshnessChecker:
    """Evaluates observation timestamps against maximum acceptable latency."""

    @staticmethod
    def evaluate_freshness(
        records: List[EvidenceRecordSchema],
        max_age_hours: Optional[int] = None,
    ) -> List[EvidenceRecordSchema]:
        """Flag records exceeding maximum acceptable age as STALE.

        Applies domain-specific freshness rules:
        - River gauge stages (CWC / RIVER_GAUGE): max 12 hours (rapid river fluctuation)
        - Precipitation forecasts (IMD / WEATHER_API): max 24 hours
        - Dam storage/outflow dispatches (BBMB / DAM_TELEMETRY): max 24 hours
        """
        now = datetime.now(timezone.utc)
        evaluated: List[EvidenceRecordSchema] = []

        for rec in records:
            # Static reference datasets (e.g. NASA SRTM elevation, baseline maps) do not decay by hourly observation age.
            # Unavailable and simulated records are also exempt from hourly staleness degradation.
            if rec.status in (EvidenceStatus.UNAVAILABLE, EvidenceStatus.SIMULATED, EvidenceStatus.STATIC_REFERENCE):
                evaluated.append(rec)
                continue

            source = (getattr(rec, "source", "") or "").upper()
            source_type = (getattr(rec, "source_type", "") or "").upper()
            param = (getattr(rec, "parameter", "") or "").lower()

            # Determine domain-specific threshold
            if max_age_hours is not None:
                threshold = max_age_hours
            elif source == "CWC" or "RIVER" in source_type or "river" in param or "water_level" in param:
                threshold = settings.RIVER_FRESHNESS_MAX_HOURS
            elif source == "IMD" or "WEATHER" in source_type or "rain" in param:
                threshold = settings.WEATHER_FRESHNESS_MAX_HOURS
            elif source == "BBMB" or "DAM" in source_type or "dam" in param or "spill" in param:
                threshold = settings.DAM_FRESHNESS_MAX_HOURS
            else:
                threshold = settings.FRESHNESS_MAX_HOURS

            # Calculate age of observation
            observed = rec.observed_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)

            age_hours = (now - observed).total_seconds() / 3600.0

            if age_hours > threshold:
                rec.status = EvidenceStatus.STALE
                rec.validation_flags.append(f"Observation is stale ({age_hours:.1f} hours old, max allowed is {threshold}h)")

            evaluated.append(rec)

        return evaluated
