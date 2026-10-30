"""Service to normalize and deduplicate heterogeneous evidence records."""

from typing import List, Dict, Any
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus


class EvidenceNormalizer:
    """Normalizes raw observations and handles deduplication."""

    @staticmethod
    def normalize_record(raw: Dict[str, Any]) -> EvidenceRecordSchema:
        """Coerce raw dictionary into normalized schema with standard types."""
        return EvidenceRecordSchema(**raw)

    @staticmethod
    def deduplicate(records: List[EvidenceRecordSchema]) -> List[EvidenceRecordSchema]:
        """Deduplicate records based on (source, parameter, observed_at)."""
        seen = set()
        unique = []
        for r in records:
            key = (r.source, r.parameter, r.observed_at.isoformat())
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

