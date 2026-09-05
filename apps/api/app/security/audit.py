"""SAMVED Phase 15: Cryptographically Chained Security Audit Trail.

Implements an append-only, tamper-evident security audit log with SHA-256 hash chaining,
ensuring verifiable provenance for high-stakes helpline compliance.
"""

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.events import UserRole, AuditStatusResult, SecurityAuditEntry


GENESIS_HASH = "0" * 64


class SecurityAuditService:
    """Thread-safe append-only audit trail with SHA-256 cryptographic chaining."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: List[SecurityAuditEntry] = []
        self._last_hash: str = GENESIS_HASH

    @staticmethod
    def compute_hash(
        prev_hash: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status_result: str,
        details: Dict[str, Any],
    ) -> str:
        """Compute deterministic SHA-256 hash over log entry fields."""
        serialized_details = json.dumps(details or {}, sort_keys=True)
        raw_payload = f"{prev_hash}|{timestamp}|{actor_id}|{actor_role}|{action}|{resource_type}|{resource_id}|{status_result}|{serialized_details}"
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def record_event(
        self,
        actor_id: str,
        actor_role: UserRole,
        action: str,
        resource_type: str,
        resource_id: str,
        status_result: AuditStatusResult = AuditStatusResult.ALLOWED,
        district_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityAuditEntry:
        """Append a new tamper-evident security audit entry to the chain."""
        now_ts = datetime.now(timezone.utc).isoformat()
        clean_details = details.copy() if details else {}

        with self._lock:
            prev_hash = self._last_hash
            entry_hash = self.compute_hash(
                prev_hash=prev_hash,
                timestamp=now_ts,
                actor_id=actor_id,
                actor_role=actor_role.value if isinstance(actor_role, UserRole) else str(actor_role),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status_result=status_result.value if isinstance(status_result, AuditStatusResult) else str(status_result),
                details=clean_details,
            )

            entry = SecurityAuditEntry(
                audit_id=f"AUD-{uuid.uuid4().hex[:10]}",
                timestamp=now_ts,
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                district_code=district_code,
                status_result=status_result,
                ip_address=ip_address,
                details=clean_details,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )

            self._entries.append(entry)
            self._last_hash = entry_hash
            return entry

    def get_entries(
        self,
        limit: int = 50,
        offset: int = 0,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        district_code: Optional[str] = None,
        status_result: Optional[AuditStatusResult] = None,
    ) -> List[SecurityAuditEntry]:
        """Query audit log entries with filtering and pagination."""
        with self._lock:
            filtered = self._entries
            if actor_id:
                filtered = [e for e in filtered if e.actor_id == actor_id]
            if action:
                filtered = [e for e in filtered if e.action == action]
            if resource_type:
                filtered = [e for e in filtered if e.resource_type == resource_type]
            if district_code:
                norm_d = district_code.strip().upper()
                filtered = [e for e in filtered if e.district_code and e.district_code.strip().upper() == norm_d]
            if status_result:
                filtered = [e for e in filtered if e.status_result == status_result]

            # Return in reverse chronological order (newest first)
            reversed_entries = list(reversed(filtered))
            return reversed_entries[offset : offset + limit]

    def verify_integrity(self) -> Tuple[bool, str, int]:
        """Verify the cryptographic hash chain from genesis to tail.
        
        Returns:
            (is_valid: bool, status_message: str, entries_verified: int)
        """
        with self._lock:
            if not self._entries:
                return True, "Audit log is empty; genesis valid.", 0

            expected_prev = GENESIS_HASH
            for idx, entry in enumerate(self._entries):
                if entry.prev_hash != expected_prev:
                    return False, f"Broken chain link at index {idx}: expected prev_hash '{expected_prev}', got '{entry.prev_hash}'", idx

                recomputed = self.compute_hash(
                    prev_hash=entry.prev_hash,
                    timestamp=entry.timestamp,
                    actor_id=entry.actor_id,
                    actor_role=entry.actor_role.value if isinstance(entry.actor_role, UserRole) else str(entry.actor_role),
                    action=entry.action,
                    resource_type=entry.resource_type,
                    resource_id=entry.resource_id,
                    status_result=entry.status_result.value if isinstance(entry.status_result, AuditStatusResult) else str(entry.status_result),
                    details=entry.details,
                )

                if recomputed != entry.entry_hash:
                    return False, f"Tampered entry hash at index {idx}: computed '{recomputed}', stored '{entry.entry_hash}'", idx

                expected_prev = entry.entry_hash

            return True, f"Cryptographic audit chain verified across all {len(self._entries)} entries.", len(self._entries)

    def total_count(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Reset the audit chain (used in test suites)."""
        with self._lock:
            self._entries.clear()
            self._last_hash = GENESIS_HASH


# Global Singleton Audit Service
_global_audit_service = SecurityAuditService()


def get_audit_service() -> SecurityAuditService:
    return _global_audit_service
