"""FollowupService: Central domain service governing follow-up workflows and care continuity."""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from app.cases.models import CaseEvidenceLink
from app.cases.service import get_case_service
from app.followup.audit import get_audit_logger
from app.followup.consent import apply_consent_revocation
from app.followup.events import create_followup_event
from app.followup.models import (
    ContactPreferences,
    FollowupAttempt,
    FollowupConsent,
    FollowupEvent,
    FollowupRecord,
    FollowupWorkqueueSummary,
)
from app.followup.policy import (
    check_duplicate_followup,
    check_max_attempts,
    check_safety_precedence,
    validate_consent_for_channel,
    validate_purpose,
    validate_safe_contact_window,
)
from app.followup.scheduler import FollowupScheduler, SystemTimeProvider, TimeProvider
from app.followup.schemas import (
    ApproveFollowupRequest,
    AssignFollowupRequest,
    CancelFollowupRequest,
    CompleteFollowupRequest,
    CreateFollowupRequest,
    RecordAttemptRequest,
    RescheduleFollowupRequest,
    RevokeConsentRequest,
    ScheduleFollowupRequest,
    StartFollowupRequest,
)
from app.realtime.connection_manager import manager
from app.schemas.events import (
    ConsentState,
    ContactChannel,
    ContactResult,
    EntityType,
    EventEnvelope,
    EventType,
    FollowupOutcome,
    FollowupPriority,
    FollowupStatus,
    FollowupType,
    RecurrenceRule,
    RelationshipType,
)

logger = logging.getLogger("samved.followup.service")


class FollowupService:
    """Thread-safe domain service managing follow-up lifecycles, scheduler, and case continuity."""

    def __init__(self, time_provider: Optional[TimeProvider] = None, auto_seed: bool = True):
        self._followups: Dict[str, FollowupRecord] = {}  # followup_id -> FollowupRecord
        self._attempts: Dict[str, List[FollowupAttempt]] = {}  # followup_id -> List[FollowupAttempt]
        self._consents: Dict[str, List[FollowupConsent]] = {}  # case_id -> List[FollowupConsent]
        self._events: Dict[str, List[FollowupEvent]] = {}  # followup_id -> List[FollowupEvent]
        self._lock = asyncio.Lock()
        self._audit_logger = get_audit_logger()
        self._time_provider = time_provider or SystemTimeProvider()
        self._scheduler = FollowupScheduler(time_provider=self._time_provider)

        if auto_seed:
            self._seed_default_fixtures()

    def set_time_provider(self, provider: TimeProvider) -> None:
        """Allows injecting FrozenTimeProvider during testing."""
        self._time_provider = provider
        self._scheduler = FollowupScheduler(time_provider=provider)

    def _seed_default_fixtures(self) -> None:
        """Seeds baseline follow-up tasks for case-1001."""
        now = self._time_provider.now()
        today_evening = now.replace(hour=18, minute=30, second=0, microsecond=0)
        due_evening = today_evening + timedelta(hours=2)

        f1 = FollowupRecord(
            followup_id="fol-1001",
            case_id="case-1001",
            call_id="call-fixture-01",
            created_by="operator",
            assigned_to="operator",
            type=FollowupType.HUMAN_CALLBACK,
            status=FollowupStatus.SCHEDULED,
            priority=FollowupPriority.HIGH,
            requested_at=now.isoformat(),
            scheduled_for=today_evening.isoformat(),
            due_at=due_evening.isoformat(),
            consent_state=ConsentState.GRANTED,
            contact_preferences=ContactPreferences(
                preferred_channel=ContactChannel.OPERATOR_CALLBACK,
                preferred_time_window="18:00-20:00",
                safe_to_contact=True,
                human_only=True,
                no_voicemail=True,
            ),
            safe_contact_window="18:00-20:00",
            channel=ContactChannel.OPERATOR_CALLBACK,
            purpose="Human callback to verify referred emergency shelter intake.",
            notes_ref="note-shelter-01",
            citation_ref="cit:central_act:p01:sec3",
            source_event="turn:5",
            max_attempts=2,
            attempt_count=0,
            policy_version="v1.0",
        )
        self._followups[f1.followup_id] = f1
        self._attempts[f1.followup_id] = []
        self._events[f1.followup_id] = []

        # Second fixture for review
        f2 = FollowupRecord(
            followup_id="fol-1002",
            case_id="case-1001",
            call_id="call-fixture-01",
            created_by="supervisor",
            assigned_to="operator",
            type=FollowupType.CASE_REVIEW,
            status=FollowupStatus.READY,
            priority=FollowupPriority.NORMAL,
            requested_at=now.isoformat(),
            scheduled_for=(now - timedelta(minutes=15)).isoformat(),
            due_at=(now + timedelta(hours=1)).isoformat(),
            consent_state=ConsentState.NOT_APPLICABLE,
            channel=ContactChannel.INTERNAL_TASK,
            purpose="Supervisory review of SVI trend and shelter referral.",
            max_attempts=1,
            attempt_count=0,
        )
        self._followups[f2.followup_id] = f2
        self._attempts[f2.followup_id] = []
        self._events[f2.followup_id] = []

    async def _emit_event(self, event: EventEnvelope) -> None:
        """Broadcasts event over operator WebSockets and records to audit log."""
        try:
            await manager.broadcast_to_operators(event)
        except Exception as e:
            logger.warning(f"Could not broadcast realtime follow-up event {event.event_type}: {e}")

    async def create_followup(
        self, case_id: str, req: CreateFollowupRequest
    ) -> Tuple[FollowupRecord, List[str]]:
        """Creates a new follow-up record with deterministic policy enforcement."""
        async with self._lock:
            # 1. Validate purpose
            purpose_decision = validate_purpose(req.purpose)
            if not purpose_decision.allowed:
                raise ValueError(f"{purpose_decision.reason_code}: {purpose_decision.message}")

            # 2. Check duplicate follow-up
            dup_decision = check_duplicate_followup(
                case_id, req.purpose, req.channel, list(self._followups.values())
            )
            if not dup_decision.allowed:
                raise ValueError(f"{dup_decision.reason_code}: {dup_decision.message}")

            # 3. Validate consent for channel
            prefs = req.contact_preferences or ContactPreferences()
            consent_decision = validate_consent_for_channel(
                req.consent_state, req.channel, prefs
            )
            if not consent_decision.allowed:
                raise ValueError(f"{consent_decision.reason_code}: {consent_decision.message}")

            # 4. Safe window check
            if req.safe_contact_window:
                window_decision = validate_safe_contact_window(
                    req.safe_contact_window, req.scheduled_for
                )
                if not window_decision.allowed:
                    raise ValueError(f"{window_decision.reason_code}: {window_decision.message}")

            # 5. Default due_at if not provided
            now = self._time_provider.now()
            due_at = req.due_at or self._scheduler.calculate_default_due_at(req.scheduled_for)

            # Determine initial status
            initial_status = FollowupStatus.SCHEDULED
            if req.consent_state in (ConsentState.UNKNOWN, ConsentState.REQUESTED):
                initial_status = FollowupStatus.DRAFT

            followup = FollowupRecord(
                followup_id=f"fol-{uuid.uuid4().hex[:10]}",
                case_id=case_id,
                call_id=req.call_id,
                created_by=req.operator_id,
                assigned_to=req.assigned_to or req.operator_id,
                type=req.type,
                status=initial_status,
                priority=req.priority,
                requested_at=now.isoformat(),
                scheduled_for=req.scheduled_for,
                due_at=due_at,
                consent_state=req.consent_state,
                contact_preferences=prefs,
                safe_contact_window=req.safe_contact_window,
                channel=req.channel,
                purpose=req.purpose,
                notes_ref=req.notes_ref,
                citation_ref=req.citation_ref,
                recurrence=req.recurrence,
                recurrence_max=req.recurrence_max,
                recurrence_count=0,
                policy_version="v1.0",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )

            self._followups[followup.followup_id] = followup
            self._attempts[followup.followup_id] = []
            self._events[followup.followup_id] = []

            # Audit record
            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=case_id,
                actor_id=req.operator_id,
                action="CREATED",
                new_status=followup.status,
                reason="Operator created follow-up task",
                details={"purpose": req.purpose, "type": req.type.value},
            )

        # Integration with Case Graph
        warnings: List[str] = []
        try:
            case_svc = get_case_service()
            case = await case_svc.get_case(case_id)
            if case:
                # Add follow-up entity to graph
                fol_entity = await case_svc.add_entity(
                    case_id=case_id,
                    entity_type=EntityType.FOLLOW_UP,
                    label=f"Follow-up: {followup.type.value}",
                    source_refs=[f"fol:{followup.followup_id}"],
                    metadata={
                        "followup_id": followup.followup_id,
                        "purpose": followup.purpose,
                        "priority": followup.priority.value,
                        "status": followup.status.value,
                    },
                )
                # Find caller or primary entity to link
                entities = await case_svc.get_graph(case_id, max_depth=1)
                primary_ent = next((n for n in entities.nodes if n.type == EntityType.PERSON), None)
                if primary_ent:
                    await case_svc.add_relationship(
                        case_id=case_id,
                        source_entity=primary_ent.entity_id,
                        relationship_type=RelationshipType.HAS_FOLLOW_UP,
                        target_entity=fol_entity.entity_id,
                        source_refs=[f"fol:{followup.followup_id}"],
                    )
        except Exception as e:
            logger.warning(f"Could not link follow-up {followup.followup_id} to case graph: {e}")
            warnings.append(f"Case graph linking deferred: {str(e)}")

        # Broadcast realtime event
        event = create_followup_event(
            EventType.FOLLOWUP_CREATED,
            followup,
            actor_id=req.operator_id,
            reason="Follow-up created",
        )
        await self._emit_event(event)

        return followup, warnings

    async def approve_followup(self, followup_id: str, req: ApproveFollowupRequest) -> FollowupRecord:
        """Approves a pending or draft follow-up and transitions it to SCHEDULED."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            if followup.status not in (FollowupStatus.DRAFT, FollowupStatus.PENDING_APPROVAL):
                raise ValueError(f"Cannot approve follow-up in status {followup.status}.")

            prev_status = followup.status
            followup.status = FollowupStatus.SCHEDULED
            followup.updated_at = self._time_provider.now().isoformat()

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="APPROVED",
                previous_status=prev_status,
                new_status=followup.status,
                reason=req.notes or "Approved by operator/supervisor",
            )

        event = create_followup_event(
            EventType.FOLLOWUP_APPROVED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
            reason=req.notes,
        )
        await self._emit_event(event)
        return followup

    async def schedule_followup(self, followup_id: str, req: ScheduleFollowupRequest) -> FollowupRecord:
        """Schedules or updates scheduled time for a follow-up."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            if req.safe_contact_window:
                window_decision = validate_safe_contact_window(
                    req.safe_contact_window, req.scheduled_for
                )
                if not window_decision.allowed:
                    raise ValueError(f"{window_decision.reason_code}: {window_decision.message}")
                followup.safe_contact_window = req.safe_contact_window

            prev_status = followup.status
            followup.scheduled_for = req.scheduled_for
            followup.due_at = req.due_at or self._scheduler.calculate_default_due_at(req.scheduled_for)
            followup.status = FollowupStatus.SCHEDULED
            followup.updated_at = self._time_provider.now().isoformat()

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="SCHEDULED",
                previous_status=prev_status,
                new_status=followup.status,
                reason="Task scheduled",
                details={"scheduled_for": req.scheduled_for},
            )

        event = create_followup_event(
            EventType.FOLLOWUP_SCHEDULED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
        )
        await self._emit_event(event)
        return followup

    async def assign_followup(self, followup_id: str, req: AssignFollowupRequest) -> FollowupRecord:
        """Assigns a follow-up task to a specific authorized operator."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            prev_assigned = followup.assigned_to
            followup.assigned_to = req.assigned_to
            followup.updated_at = self._time_provider.now().isoformat()

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="ASSIGNED",
                reason=f"Reassigned from {prev_assigned} to {req.assigned_to}",
                details={"assigned_to": req.assigned_to},
            )

        return followup

    async def start_followup(self, followup_id: str, req: StartFollowupRequest) -> FollowupRecord:
        """Transitions a READY or SCHEDULED follow-up into IN_PROGRESS."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            if followup.status not in (FollowupStatus.SCHEDULED, FollowupStatus.READY):
                raise ValueError(f"Cannot start follow-up currently in status {followup.status}.")

            prev_status = followup.status
            followup.status = FollowupStatus.IN_PROGRESS
            followup.updated_at = self._time_provider.now().isoformat()

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="STARTED",
                previous_status=prev_status,
                new_status=followup.status,
                reason="Operator started follow-up action",
            )

        event = create_followup_event(
            EventType.FOLLOWUP_STARTED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
        )
        await self._emit_event(event)
        return followup

    async def record_attempt(self, followup_id: str, req: RecordAttemptRequest) -> Tuple[FollowupRecord, FollowupAttempt]:
        """Records an execution attempt against a follow-up task."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            # Check attempt cap
            max_check = check_max_attempts(followup)
            if not max_check.allowed:
                raise ValueError(f"{max_check.reason_code}: {max_check.message}")

            now_iso = self._time_provider.now().isoformat()
            followup.attempt_count += 1
            followup.last_attempt_at = now_iso
            followup.updated_at = now_iso

            attempt = FollowupAttempt(
                followup_id=followup_id,
                case_id=followup.case_id,
                attempt_number=followup.attempt_count,
                attempted_at=now_iso,
                operator_id=req.operator_id,
                channel=req.channel,
                result=req.result,
                notes=req.notes,
            )
            self._attempts.setdefault(followup_id, []).append(attempt)

            prev_status = followup.status
            # If caller declined, immediately block future automated outreach
            if req.result == ContactResult.CALLER_DECLINED:
                followup.status = FollowupStatus.BLOCKED
                followup.consent_state = ConsentState.REFUSED
                followup.blocked_reason = "CALLER_DECLINED: Caller declined follow-up contact."
                self._audit_logger.log(
                    followup_id=followup.followup_id,
                    case_id=followup.case_id,
                    actor_id=req.operator_id,
                    action="BLOCKED",
                    previous_status=prev_status,
                    new_status=followup.status,
                    reason="Caller declined contact",
                )
            else:
                self._audit_logger.log(
                    followup_id=followup.followup_id,
                    case_id=followup.case_id,
                    actor_id=req.operator_id,
                    action="ATTEMPTED",
                    reason=f"Attempt {followup.attempt_count}: {req.result}",
                    details={"result": str(req.result), "channel": str(req.channel)},
                )

        event = create_followup_event(
            EventType.FOLLOWUP_ATTEMPT_RECORDED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
            attempt=attempt,
        )
        await self._emit_event(event)
        return followup, attempt

    async def complete_followup(self, followup_id: str, req: CompleteFollowupRequest) -> FollowupRecord:
        """Completes a follow-up task with structured outcome, notes, and bounded recurrence."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            if followup.status == FollowupStatus.COMPLETED:
                # Idempotent response
                return followup

            prev_status = followup.status
            now_iso = self._time_provider.now().isoformat()
            followup.status = FollowupStatus.COMPLETED
            followup.completed_at = now_iso
            followup.outcome = req.outcome
            if req.notes_ref:
                followup.notes_ref = req.notes_ref
            followup.updated_at = now_iso

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="COMPLETED",
                previous_status=prev_status,
                new_status=followup.status,
                reason=f"Completed with outcome: {req.outcome}",
                details={"outcome": str(req.outcome)},
            )

        # Recurrence check
        next_rec = self._scheduler.calculate_next_recurrence(followup)
        if next_rec:
            next_sched, next_due = next_rec
            req_next = CreateFollowupRequest(
                call_id=followup.call_id,
                type=followup.type,
                priority=followup.priority,
                channel=followup.channel,
                purpose=followup.purpose,
                scheduled_for=next_sched,
                due_at=next_due,
                consent_state=followup.consent_state,
                contact_preferences=followup.contact_preferences,
                safe_contact_window=followup.safe_contact_window,
                assigned_to=followup.assigned_to,
                recurrence=followup.recurrence,
                recurrence_max=followup.recurrence_max,
                operator_id=req.operator_id,
            )
            try:
                next_f, _ = await self.create_followup(followup.case_id, req_next)
                next_f.recurrence_count = followup.recurrence_count + 1
                logger.info(f"Generated next recurring follow-up {next_f.followup_id} (iteration {next_f.recurrence_count}).")
            except Exception as e:
                logger.warning(f"Could not generate recurring follow-up for {followup_id}: {e}")

        event = create_followup_event(
            EventType.FOLLOWUP_COMPLETED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
            reason=f"Completed with outcome {req.outcome}",
        )
        await self._emit_event(event)
        return followup

    async def reschedule_followup(self, followup_id: str, req: RescheduleFollowupRequest) -> FollowupRecord:
        """Reschedules a task to a new time window."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            if followup.status in (FollowupStatus.COMPLETED, FollowupStatus.CANCELLED):
                raise ValueError(f"Cannot reschedule a task in terminal status {followup.status}.")

            if req.safe_contact_window:
                window_decision = validate_safe_contact_window(
                    req.safe_contact_window, req.scheduled_for
                )
                if not window_decision.allowed:
                    raise ValueError(f"{window_decision.reason_code}: {window_decision.message}")
                followup.safe_contact_window = req.safe_contact_window

            prev_status = followup.status
            followup.scheduled_for = req.scheduled_for
            followup.due_at = req.due_at or self._scheduler.calculate_default_due_at(req.scheduled_for)
            followup.status = FollowupStatus.SCHEDULED
            followup.updated_at = self._time_provider.now().isoformat()

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="RESCHEDULED",
                previous_status=prev_status,
                new_status=followup.status,
                reason=req.reason,
                details={"new_scheduled_for": req.scheduled_for},
            )

        event = create_followup_event(
            EventType.FOLLOWUP_RESCHEDULED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
            reason=req.reason,
        )
        await self._emit_event(event)
        return followup

    async def cancel_followup(self, followup_id: str, req: CancelFollowupRequest) -> FollowupRecord:
        """Cancels a follow-up task with an auditable reason."""
        async with self._lock:
            followup = self._followups.get(followup_id)
            if not followup:
                raise KeyError(f"Follow-up {followup_id} not found.")

            if followup.status == FollowupStatus.COMPLETED:
                raise ValueError("Cannot cancel an already completed follow-up task.")

            prev_status = followup.status
            now_iso = self._time_provider.now().isoformat()
            followup.status = FollowupStatus.CANCELLED
            followup.cancelled_at = now_iso
            followup.updated_at = now_iso

            self._audit_logger.log(
                followup_id=followup.followup_id,
                case_id=followup.case_id,
                actor_id=req.operator_id,
                action="CANCELLED",
                previous_status=prev_status,
                new_status=followup.status,
                reason=req.reason,
            )

        event = create_followup_event(
            EventType.FOLLOWUP_CANCELLED,
            followup,
            actor_id=req.operator_id,
            previous_status=prev_status,
            reason=req.reason,
        )
        await self._emit_event(event)
        return followup

    async def revoke_consent(self, case_id: str, req: RevokeConsentRequest) -> List[FollowupRecord]:
        """Revokes caller consent for a case, immediately cascading BLOCKED state to all active tasks."""
        async with self._lock:
            blocked_tasks, consent_rec = apply_consent_revocation(
                case_id, list(self._followups.values()), req.reason, req.operator_id
            )
            self._consents.setdefault(case_id, []).append(consent_rec)

            for task in blocked_tasks:
                self._audit_logger.log(
                    followup_id=task.followup_id,
                    case_id=case_id,
                    actor_id=req.operator_id,
                    action="BLOCKED",
                    new_status=FollowupStatus.BLOCKED,
                    reason=f"CONSENT_REVOKED: {req.reason}",
                )

        # Broadcast events for each blocked task
        for task in blocked_tasks:
            event = create_followup_event(
                EventType.FOLLOWUP_BLOCKED,
                task,
                actor_id=req.operator_id,
                reason=f"CONSENT_REVOKED: {req.reason}",
            )
            await self._emit_event(event)

        return blocked_tasks

    async def evaluate_all_tasks(self) -> List[FollowupRecord]:
        """Evaluates readiness and deadlines across all active scheduled tasks."""
        async with self._lock:
            mutated: List[FollowupRecord] = []
            for f in self._followups.values():
                if f.status in (FollowupStatus.SCHEDULED, FollowupStatus.READY):
                    new_status, reason = self._scheduler.evaluate_task_readiness(f)
                    if new_status != f.status:
                        prev = f.status
                        f.status = new_status
                        f.updated_at = self._time_provider.now().isoformat()
                        mutated.append(f)
                        self._audit_logger.log(
                            followup_id=f.followup_id,
                            case_id=f.case_id,
                            actor_id="scheduler",
                            action="STATUS_CHANGED",
                            previous_status=prev,
                            new_status=new_status,
                            reason=reason or "Temporal readiness evaluated by scheduler",
                        )
            return mutated

    async def get_followup(self, followup_id: str) -> Optional[FollowupRecord]:
        """Retrieves a single follow-up task."""
        return self._followups.get(followup_id)

    async def get_attempts(self, followup_id: str) -> List[FollowupAttempt]:
        """Retrieves contact attempt logs for a follow-up task."""
        return self._attempts.get(followup_id, [])

    async def list_followups(
        self,
        case_id: Optional[str] = None,
        status: Optional[Union[FollowupStatus, str]] = None,
        priority: Optional[Union[FollowupPriority, str]] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FollowupRecord], int]:
        """Lists follow-up tasks matching query filters."""
        # First evaluate temporal readiness so list is fresh
        await self.evaluate_all_tasks()

        items = list(self._followups.values())
        if case_id:
            items = [f for f in items if f.case_id == case_id]
        if status:
            status_val = status.value if isinstance(status, FollowupStatus) else status
            items = [f for f in items if f.status.value == status_val]
        if priority:
            priority_val = priority.value if isinstance(priority, FollowupPriority) else priority
            items = [f for f in items if f.priority.value == priority_val]
        if assigned_to:
            items = [f for f in items if f.assigned_to == assigned_to]

        # Sort: CRITICAL/HIGH first, then by scheduled_for
        priority_order = {
            FollowupPriority.CRITICAL_REVIEW: 0,
            FollowupPriority.HIGH: 1,
            FollowupPriority.NORMAL: 2,
            FollowupPriority.LOW: 3,
        }
        items.sort(key=lambda x: (priority_order.get(x.priority, 2), x.scheduled_for))

        total = len(items)
        return items[offset : offset + limit], total

    async def get_workqueue_summary(self, case_id: Optional[str] = None) -> FollowupWorkqueueSummary:
        """Computes summary metrics for the operator workstation."""
        await self.evaluate_all_tasks()
        now = self._time_provider.now()
        today_str = now.strftime("%Y-%m-%d")

        all_items = list(self._followups.values())
        if case_id:
            all_items = [f for f in all_items if f.case_id == case_id]

        active_statuses = {
            FollowupStatus.SCHEDULED,
            FollowupStatus.READY,
            FollowupStatus.IN_PROGRESS,
        }

        total_active = sum(1 for f in all_items if f.status in active_statuses)
        due_today = sum(
            1 for f in all_items
            if f.status in active_statuses and f.scheduled_for.startswith(today_str)
        )
        overdue = sum(1 for f in all_items if f.status == FollowupStatus.MISSED)
        blocked = sum(1 for f in all_items if f.status == FollowupStatus.BLOCKED)
        completed_today = sum(
            1 for f in all_items
            if f.status == FollowupStatus.COMPLETED
            and f.completed_at
            and f.completed_at.startswith(today_str)
        )

        return FollowupWorkqueueSummary(
            total_active=total_active,
            due_today=due_today,
            overdue=overdue,
            blocked=blocked,
            completed_today=completed_today,
        )


# Singleton
_followup_service_singleton: Optional[FollowupService] = None
_followup_lock = asyncio.Lock()


def get_followup_service() -> FollowupService:
    global _followup_service_singleton
    if _followup_service_singleton is None:
        _followup_service_singleton = FollowupService()
    return _followup_service_singleton
