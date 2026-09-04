# SAMVED — Safety Engine Testing & Verification Guide

This document summarizes the automated and E2E verification suites covering the Phase 4 Deterministic Safety Engine.

---

## 1. Backend Test Suites (74/74 Passed)

The backend test suite is executed using `pytest`:

```bash
uv --directory apps/api run pytest -v
```

### Key Test Suites:

1. **`tests/test_safety_engine.py` (15 Tests)**:
   - `test_unicode_normalization`: Validates that NFC normalization handles decomposed Indic characters consistently.
   - `test_clause_isolated_negation`: Verifies that `"not"` inside a clause negates a threat, but does not cross clause boundaries (`"I cannot take this anymore, I want to end my life"` correctly flags suicidal intent).
   - `test_temporal_classification`: Verifies `PRESENT`, `PAST`, and `HYPOTHETICAL` context tags across English, Tamil, and Hindi.
   - `test_active_physical_threat_en`: Asserts `ONGOING_THREAT` on `"He is breaking into my door and trying to hit me"`.
   - `test_active_physical_threat_ta`: Asserts `ONGOING_THREAT` on `"என்னை அடிக்கிறார் காப்பாற்றுங்கள்"`.
   - `test_active_physical_threat_hi`: Asserts `ONGOING_THREAT` on `"वह मुझे बहुत मार रहा है"`.
   - `test_compound_weapon_escalation`: Verifies that `"knife"` + `"breaking into my house"` triggers `WEAPON_PRESENCE` with `CRITICAL` severity.
   - `test_weapon_false_positive_suppression`: Verifies that kitchen cooking mentions (`"cutting vegetables with a knife"`) do **not** trigger safety alarms.
   - `test_self_harm_crisis`: Asserts `SELF_HARM_CRISIS` with `CRITICAL` severity across all supported languages.
   - `test_confinement_detection`: Asserts `CONFINEMENT` on `"locked inside the room"`.
   - `test_medical_emergency`: Asserts `MEDICAL_EMERGENCY` on `"severe bleeding and unconscious"`.
   - `test_coercion_intimidation`: Asserts `COERCION` on extortion and leak threats.
   - `test_multi_turn_deduplication`: Verifies identical signals are not re-emitted on consecutive turns, but call-level safety state is preserved.
   - `test_engine_determinism_and_latency`: Benchmarks 100 consecutive evaluations; asserts all complete in **< 5ms** (actual average: 0.2ms).

2. **`tests/test_safety_api.py` (6 Tests)**:
   - `test_safety_status`: Verifies `GET /v1/safety/status` returns engine version and rule counts.
   - `test_safety_rules_catalog`: Verifies `GET /v1/safety/rules` returns all versioned rule schemas.
   - `test_safety_evaluate_threat`: Verifies `POST /v1/safety/evaluate` evaluates threats deterministically.
   - `test_safety_evaluate_negation`: Verifies `POST /v1/safety/evaluate` handles explicit negation.
   - `test_get_call_safety`: Verifies `GET /v1/safety/calls/{call_id}` returns call safety state.
   - `test_acknowledge_safety_signal`: Verifies `POST /v1/safety/calls/{call_id}/acknowledge` records operator audit log.

3. **`tests/test_safety_concurrency.py` (1 Test)**:
   - Tests concurrent incoming calls to ensure safety states and active signals are strictly isolated per call ID.

---

## 2. Frontend Playwright E2E Test Suite

Playwright tests are executed using:

```bash
pnpm --filter @samved/web test:e2e
```

### Coverage in `apps/web/e2e/safety-engine.spec.ts`:
- **Safety Engine Status Indicator**: Confirms header displays engine version and ready state.
- **Rules Catalog Modal**: Opens modal, validates loaded rules (`RULE_THREAT_001`, `RULE_WEAPON_002`), closes modal.
- **Interactive Safety Lab**:
  - Tests Active Weapon Threat preset -> asserts `CRITICAL` state, `Requires Human Review`, matched phrase.
  - Tests Negated Threat Cue preset -> asserts `NONE` state, no false alarms.
- **Operator Console Oversight Banner & Acknowledgment**:
  - Renders active call with CRITICAL alert.
  - Clicks "Acknowledge Alert" -> records operator audit trail in real time.
