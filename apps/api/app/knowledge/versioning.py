"""Document version management, supersession tracking, and temporal applicability."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.knowledge.models import (
    DocumentStatus,
    DocumentVersion,
    FreshnessStatus,
    SourceDocument,
)


def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses ISO-8601 date string to timezone-aware UTC datetime."""
    if not date_str:
        return None
    try:
        # Support YYYY-MM-DD and full ISO-8601
        if len(date_str) == 10:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def calculate_freshness(
    effective_from: str,
    effective_to: Optional[str],
    status: DocumentStatus,
    as_of_date: Optional[str] = None,
) -> FreshnessStatus:
    """Calculates freshness state of a document version relative to a target date."""
    target_dt = parse_iso_date(as_of_date) or datetime.now(timezone.utc)
    eff_from_dt = parse_iso_date(effective_from)
    eff_to_dt = parse_iso_date(effective_to)

    if status == DocumentStatus.SUPERSEDED:
        return FreshnessStatus.STALE

    if status == DocumentStatus.RETIRED:
        return FreshnessStatus.EXPIRED

    if eff_to_dt and target_dt > eff_to_dt:
        return FreshnessStatus.EXPIRED

    if eff_from_dt and target_dt < eff_from_dt:
        return FreshnessStatus.UNKNOWN

    return FreshnessStatus.CURRENT


def is_version_effective(
    effective_from: str,
    effective_to: Optional[str],
    as_of_date: Optional[str] = None,
) -> bool:
    """Checks if a document version is effective at the given as_of_date."""
    target_dt = parse_iso_date(as_of_date) or datetime.now(timezone.utc)
    eff_from_dt = parse_iso_date(effective_from)
    eff_to_dt = parse_iso_date(effective_to)

    if eff_from_dt and target_dt < eff_from_dt:
        return False

    if eff_to_dt and target_dt > eff_to_dt:
        return False

    return True


class VersionManager:
    """Manages version lifecycles, superseding links, and active document state."""

    @staticmethod
    def add_version(
        document: SourceDocument,
        new_version: DocumentVersion,
        auto_supersede_previous: bool = True,
    ) -> SourceDocument:
        """Appends new version to document and marks previous version SUPERSEDED if requested."""
        if auto_supersede_previous and document.versions:
            # Find current active version
            for prev in document.versions:
                if prev.status == DocumentStatus.ACTIVE:
                    prev.status = DocumentStatus.SUPERSEDED
                    prev.superseded_by = new_version.version_number
                    new_version.supersedes = prev.version_number

        document.versions.append(new_version)
        document.current_version = new_version.version_number
        document.effective_from = new_version.effective_from
        document.effective_to = new_version.effective_to
        document.status = new_version.status
        document.content_hash = new_version.content_hash
        document.checksum = new_version.checksum
        return document

    @staticmethod
    def get_active_version(document: SourceDocument) -> Optional[DocumentVersion]:
        """Returns the currently ACTIVE version of the document."""
        for v in reversed(document.versions):
            if v.status == DocumentStatus.ACTIVE:
                return v
        return None

    @staticmethod
    def get_version_by_number(
        document: SourceDocument, version_number: str
    ) -> Optional[DocumentVersion]:
        """Returns a specific version by its version number."""
        for v in document.versions:
            if v.version_number == version_number:
                return v
        return None
