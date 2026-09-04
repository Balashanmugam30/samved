# SAMVED Architecture: Phase 7 — Adaptive Conversation Engine

## 1. Architectural Overview & Philosophy

The **Adaptive Conversation Engine** serves as SAMVED's deterministic conversational policy layer. It answers the fundamental operational question at every turn:

> **"Given known state and structured evidence, what should SAMVED do next?"**

### Core Tenets & Non-Negotiable Boundaries:
1. **Safety Precedence is Inviolable**: Phase 4 Deterministic Safety Engine is authoritative. The adaptive engine can escalate or constrain conversational action, but can NEVER downgrade or override a safety decision.
2. **LLM as Surface Realization Only**: The Large Language Model (`gemini-2.5-flash`) acts strictly as a surface realization layer bounded by deterministic policy envelopes, forbidden claims, and word count constraints. If validation fails, deterministic localized fallback templates are immediately returned.
3. **Strict Information-Gap Planning**: Questions are asked only when required information is absent. Once established, facts are retained and never re-asked unless explicitly contradicted by the caller.
4. **Minimum Necessary Question Policy**: No more than ONE question may be posed per conversational turn to prevent overwhelming vulnerable callers.
5. **Bounded Repetition**: Clarification or information requests are limited to at most 2 attempts. Persistent ambiguity or caller refusal triggers immediate escalation or human counselor handoff.
6. **Contradiction-Aware State Management**: Caller statements that contradict earlier facts immediately supersede stale facts with logged reason codes.
7. **Human-Supervised with Instant Override**: Human operators can force human handoff, pause questioning for supportive silence, or trigger explicit safety checks at any time.
8. **Non-Clinical Guarantee**: The engine is an operational triage strategy layer. It is NOT a therapist, diagnostic tool, psychiatric classifier, lie detector, or autonomous emergency dispatch system.

---

## 2. Policy Precedence Hierarchy (P0–P5)

The engine evaluates every turn against an inviolable priority cascade:

| Priority | Tier | Trigger Conditions | Permitted Actions |
| :--- | :--- | :--- | :--- |
| **P0** | **Critical Safety** | `CRITICAL` safety signal, immediate weapon/physical danger, or operator `operator_force_human` | `SAFETY_CHECK`, `HUMAN_HANDOFF`, `ASK_IMMEDIATE_DANGER` |
| **P1** | **Elevated Safety** | `HIGH`/`ELEVATED` safety state, explicit caller request for human (`requests_human`), or ongoing threat signal | `SAFETY_CHECK`, `HUMAN_HANDOFF`, `ASK_SAFE_TO_CONTINUE` |
| **P2** | **High SVI Vulnerability** | $SVI \ge 76$ (`CRITICAL` band) or $SVI \ge 51$ with rising trend | `SAFETY_CHECK`, `PROVIDE_REASSURANCE`, `ASK_SUPPORT` |
| **P3** | **Operational Degradation** | `POOR` acoustic quality, severe packet loss, or high speech ambiguity | `CLARIFY_AUDIO`, `ALLOW_SILENCE`, `REPEAT_LAST` |
| **P4** | **Clarification & Support** | Missing operational triage facts (immediate danger, location, support domain) | `ASK_IMMEDIATE_DANGER`, `ASK_LOCATION`, `ASK_SUPPORT`, `ACKNOWLEDGE_AND_VALIDATE` |
| **P5** | **Closure** | Caller expresses closure intent (`affirms_safe`, gratitude/goodbye) | `SUMMARIZE_AND_CONFIRM`, `OFFER_RESOURCES`, `END_GRACEFULLY` |

---

## 3. Component Architecture

```
                                  +-----------------------------+
                                  | Telephony / Ingress (8kHz)  |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |    Turn Pipeline Intake     |
                                  |  - STT Transcription        |
                                  |  - Deterministic Safety     |
                                  |  - Acoustic Telemetry       |
                                  |  - SVI 0-100 Calculation    |
                                  +--------------+--------------+
                                                 |
                                                 v
+------------------------+        +-----------------------------+        +------------------------+
| Operator Overrides     | -----> |   Adaptive Engine Service   | <----- | Session Fact Store     |
| - force_human          |        |   (evaluate_turn)           |        | - immediate_danger     |
| - pause_adaptive       |        +--------------+--------------+        | - safe_to_continue     |
| - request_safety_check |                       |                       | - location_stated      |
+------------------------+                       v                       | - support_domain       |
                                  +-----------------------------+        +------------------------+
                                  |  Deterministic Planner      |
                                  |  - Priority Matcher (P0-P5) |
                                  |  - Fact Gap Analysis        |
                                  |  - Repetition Guard (<=2)   |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  | Selected Strategy Contract  |
                                  | - Action, Priority, Target  |
                                  | - Reason Codes, Evidence    |
                                  +--------------+--------------+
                                                 |
                                                 v
                         +-----------------------+-----------------------+
                         |                                               |
                         v                                               v
          +-----------------------------+                 +-----------------------------+
          | LLM Surface Realization     |                 | Deterministic Fallback      |
          | - Formats response text     |                 | Localized Templates         |
          | - Checked by Validator:     |                 | (ta-IN, hi-IN, en-IN)       |
          |   * <=45 words              |                 | Sub-millisecond guarantee   |
          |   * <=1 question            |                 +-----------------------------+
          |   * Prohibited claim filter |
          +-----------------------------+
```

---

## 4. Response Validation & Prohibited Claims

The `ResponseValidator` verifies all LLM realizations before transmission to TTS:
1. **Word Count Bound**: Maximum 45 words per turn.
2. **Single Question Constraint**: At most 1 question mark (`?`) per turn.
3. **Forbidden Claim Detection**:
   - No police dispatch or law enforcement claims ("police are on their way").
   - No clinical diagnoses ("you have clinical depression", "you are an addict").
   - No psychiatric disorder classifications.
4. **Deterministic Fallback**: If the LLM generates a prohibited phrase, exceeds length, or contains multiple questions, the validator replaces the output with the pre-compiled localized template for the selected action.

---

## 5. Multilingual Localization

All critical fallback templates are versioned and localized across:
- **Tamil (`ta-IN`)**: Culturally grounded phrasing honoring safety and respect.
- **Hindi (`hi-IN`)**: Empathetic, de-escalating North Indian vernacular.
- **Indian English (`en-IN`)**: Clear, concise, standard Indian English phrasing.

---

## 6. Realtime Events & WebSocket Taxonomy

When an adaptive strategy is selected, the server broadcasts an event over `/ws/operator`:
- **Event Type**: `EventType.ADAPTIVE_STRATEGY_SELECTED`
- **Payload Schema**:
  ```typescript
  export interface AdaptiveStrategySelectedPayload {
    call_id: string;
    session_id: string;
    turn_index: number;
    action: string;
    priority: string;
    target_information: string;
    reason_codes: string[];
    evidence_refs: string[];
    language: string;
    confidence: number;
    requires_human_review?: boolean;
    operator_override_active?: boolean;
    fallback_applied?: boolean;
    disclaimer?: string;
    evaluated_at: string;
  }
  ```

---

## 7. REST APIs

- `GET /v1/adaptive/status`: Operational health, active policy count, non-clinical boundaries.
- `GET /v1/adaptive/policy`: Catalog of 17 deterministic conversational actions, priority tiers, and reason codes.
- `POST /v1/adaptive/plan`: Standalone simulation endpoint for testing scenarios.
- `GET /v1/adaptive/calls/{call_id}`: Active strategy for a specific call.
- `GET /v1/adaptive/calls/{call_id}/history`: Chronological turn-by-turn strategy trajectory.
- `POST /v1/adaptive/calls/{call_id}/override`: Operator command execution (`operator_force_human`, `operator_pause_adaptive`, `operator_resume_adaptive`, `operator_request_safety_check`).
