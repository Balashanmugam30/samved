"""Temporal Graph & Historical Preservation Layer (Phase 11)."""

from datetime import datetime, timezone
from typing import List, Optional
from app.cases.models import CaseEvent, CaseRelationship


def parse_iso_datetime(dt_str: str) -> datetime:
    """Safely parses ISO-8601 UTC timestamp strings."""
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


def is_edge_active_at(edge: CaseRelationship, as_of: Optional[datetime] = None) -> bool:
    """Evaluates whether an edge is valid and active as of a given timestamp (default: now)."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    # Check start validity
    try:
        from_dt = parse_iso_datetime(edge.valid_from)
        if as_of < from_dt:
            return False
    except Exception:
        pass

    # Check end validity
    if edge.valid_to:
        try:
            to_dt = parse_iso_datetime(edge.valid_to)
            if as_of > to_dt:
                return False
        except Exception:
            pass

    # Check superseded timestamp
    if edge.superseded_at:
        try:
            sup_dt = parse_iso_datetime(edge.superseded_at)
            if as_of >= sup_dt:
                return False
        except Exception:
            pass

    return True


def supersede_edge(
    old_edge: CaseRelationship,
    new_edge_id: str,
    superseded_at: Optional[str] = None,
) -> CaseRelationship:
    """Marks a historical edge as superseded by a newer edge without erasing historical facts."""
    now_iso = superseded_at or datetime.now(timezone.utc).isoformat()
    old_edge.superseded_at = now_iso
    old_edge.superseded_by = new_edge_id
    old_edge.valid_to = now_iso
    return old_edge


def sort_events_chronologically(events: List[CaseEvent]) -> List[CaseEvent]:
    """Sorts case events chronologically by timestamp."""
    def _event_key(ev: CaseEvent):
        try:
            return parse_iso_datetime(ev.timestamp)
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    return sorted(events, key=_event_key)
