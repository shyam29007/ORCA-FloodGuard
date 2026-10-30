"""Safe state reducers for parallel agent executions in LangGraph."""

from typing import List, Dict, Any


def add_evidence_reducer(current: List[Dict[str, Any]], update: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Safely merge new evidence records into the shared evidence pool."""
    if not current:
        current = []
    if not update:
        return current
    # Deduplicate by key (source, parameter, observed_at)
    merged = list(current)
    seen = {
        (rec.get("source"), rec.get("parameter"), str(rec.get("observed_at")))
        for rec in current
    }
    for rec in update:
        key = (rec.get("source"), rec.get("parameter"), str(rec.get("observed_at")))
        if key not in seen:
            seen.add(key)
            merged.append(rec)
    return merged


def update_traces_reducer(current: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Safely merge agent execution traces."""
    res = dict(current) if current else {}
    if update:
        res.update(update)
    return res


def add_errors_reducer(current: List[str], update: List[str]) -> List[str]:
    """Safely append workflow errors."""
    res = list(current) if current else []
    if update:
        if isinstance(update, list):
            res.extend(update)
        else:
            res.append(str(update))
    return res

