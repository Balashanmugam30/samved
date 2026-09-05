"""SAMVED Phase 15: Data Retention & Privacy Lifecycle Management.

Governs time-to-live (TTL) policies, anonymization schedules, and supervisor-approved
data purging across raw audio, transcripts, analytics, and audit logs.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import HTTPException, status

from app.schemas.events import (
    UserRole,
    UserIdentity,
    DataRetentionPurgeStrategy,
    DataRetentionPolicy,
)


DEFAULT_POLICIES: List[DataRetentionPolicy] = [
    DataRetentionPolicy(
        policy_id="ret-raw-audio",
        data_category="RAW_AUDIO",
        retention_days=30,
        purge_strategy=DataRetentionPurgeStrategy.HARD_DELETE,
        requires_supervisor_approval=True,
        is_active=True,
        records_purged_count=0,
    ),
    DataRetentionPolicy(
        policy_id="ret-transcript",
        data_category="TRANSCRIPTS",
        retention_days=90,
        purge_strategy=DataRetentionPurgeStrategy.ANONYMIZE,
        requires_supervisor_approval=True,
        is_active=True,
        records_purged_count=0,
    ),
    DataRetentionPolicy(
        policy_id="ret-analytics-agg",
        data_category="ANALYTICS_AGGREGATES",
        retention_days=365,
        purge_strategy=DataRetentionPurgeStrategy.ANONYMIZE,
        requires_supervisor_approval=False,
        is_active=True,
        records_purged_count=0,
    ),
    DataRetentionPolicy(
        policy_id="ret-audit-logs",
        data_category="AUDIT_LOGS",
        retention_days=730,
        purge_strategy=DataRetentionPurgeStrategy.ARCHIVE_COLD,
        requires_supervisor_approval=True,
        is_active=True,
        records_purged_count=0,
    ),
    DataRetentionPolicy(
        policy_id="ret-training-runs",
        data_category="TRAINING_RUNS",
        retention_days=180,
        purge_strategy=DataRetentionPurgeStrategy.HARD_DELETE,
        requires_supervisor_approval=False,
        is_active=True,
        records_purged_count=0,
    ),
]


class RetentionService:
    """Manages configurable data retention rules and compliance purging."""

    def __init__(self):
        self._lock = threading.Lock()
        self._policies: Dict[str, DataRetentionPolicy] = {
            p.data_category: p.model_copy() for p in DEFAULT_POLICIES
        }

    def list_policies(self) -> List[DataRetentionPolicy]:
        with self._lock:
            return list(self._policies.values())

    def get_policy(self, data_category: str) -> Optional[DataRetentionPolicy]:
        with self._lock:
            return self._policies.get(data_category.strip().upper())

    def update_policy(
        self,
        data_category: str,
        retention_days: int,
        purge_strategy: DataRetentionPurgeStrategy,
        requires_supervisor_approval: bool,
        is_active: bool = True,
    ) -> DataRetentionPolicy:
        norm_cat = data_category.strip().upper()
        with self._lock:
            if norm_cat not in self._policies:
                self._policies[norm_cat] = DataRetentionPolicy(
                    policy_id=f"ret-{norm_cat.lower().replace('_', '-')}",
                    data_category=norm_cat,
                    retention_days=retention_days,
                    purge_strategy=purge_strategy,
                    requires_supervisor_approval=requires_supervisor_approval,
                    is_active=is_active,
                )
            else:
                p = self._policies[norm_cat]
                p.retention_days = retention_days
                p.purge_strategy = purge_strategy
                p.requires_supervisor_approval = requires_supervisor_approval
                p.is_active = is_active

            return self._policies[norm_cat].model_copy()

    def execute_purge(
        self,
        data_category: str,
        identity: UserIdentity,
        supervisor_approved: bool = False,
    ) -> Dict[str, any]:
        norm_cat = data_category.strip().upper()
        with self._lock:
            policy = self._policies.get(norm_cat)
            if not policy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Retention policy for category '{norm_cat}' not found.",
                )

            # Check supervisor authority if required
            if policy.requires_supervisor_approval:
                is_authorized_actor = identity.role in (UserRole.SUPERVISOR, UserRole.SYSTEM_ADMIN)
                if not (supervisor_approved or is_authorized_actor):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Purge of '{norm_cat}' requires explicit supervisor confirmation.",
                    )

            now_ts = datetime.now(timezone.utc).isoformat()
            # In-memory prototype purge execution simulation
            purged_count = 12  # Simulated pruned records count
            policy.last_purge_at = now_ts
            policy.records_purged_count += purged_count

            return {
                "category": norm_cat,
                "strategy": policy.purge_strategy.value,
                "records_purged": purged_count,
                "purged_at": now_ts,
                "initiated_by": identity.user_id,
                "actor_role": identity.role.value,
                "status": "COMPLETED",
            }


# Global Singleton Retention Service
_global_retention_service = RetentionService()


def get_retention_service() -> RetentionService:
    return _global_retention_service
