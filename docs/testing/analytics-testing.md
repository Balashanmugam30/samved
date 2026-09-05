# Phase 13 Testing Strategy: District Intelligence & Operational Analytics

## 1. Overview & Verification Doctrine
Testing Phase 13 validates the mathematical, privacy, and architectural invariants of SAMVED's District Intelligence and Operational Analytics engine under Smart India Hackathon 2026 (Problem Statement 26093) for NHAA 14566.

### Core Testing Pillars
1. **Mathematical Correctness**: Accurate counts, period-over-period percentages, and formulas.
2. **K-Anonymity & Small-Cell Suppression**: Guaranteed suppression when cohort $< 10$, scrubbing raw counts to prevent PII exposure.
3. **Difference Attack Defense**: Complementary suppression preventing subtraction attacks against known totals.
4. **Non-Predictive Governance**: Complete absence of crime predictions, neighborhood danger ratings, offender scores, or victim profiling.
5. **Role-Based Access Enforcement**: Explicit 403 Forbidden for unauthorized roles (e.g. `OPERATOR`).
6. **Robust Input Defense**: Resilience against SQL injection, path traversal, and out-of-bounds parameters.

---

## 2. Test Matrix

### 2.1 Backend Pytest Suite (`apps/api/tests/`)

| Test File | Test Cases | Focus Area | Status |
| :--- | :--- | :--- | :---: |
| `test_analytics_models.py` | 4 tests | Pydantic domain models, trust status mappings, timezone defaults. | ✅ PASSED |
| `test_analytics_metrics.py` | 4 tests | Metric catalog completeness, mathematical formulas, absence of predictive danger scores. | ✅ PASSED |
| `test_analytics_aggregation.py` | 3 tests | Event deduplication by `event_id`, data quality thresholds, district normalization. | ✅ PASSED |
| `test_analytics_privacy.py` | 5 tests | Cohort size checks ($k \ge 10$), raw count scrubbing, display rounding, complementary suppression. | ✅ PASSED |
| `test_analytics_suppression.py` | 3 tests | Small-cell suppression scenarios (`PY-KKL`), verified zero count leakage. | ✅ PASSED |
| `test_analytics_trends.py` | 5 tests | Deterministic period-over-period trend calculations (`RISING`, `FALLING`, `STABLE`, `INSUFFICIENT_DATA`). | ✅ PASSED |
| `test_analytics_api.py` | 13 tests | Full suite of REST endpoints, summary, trends, distributions, recompute, and audit. | ✅ PASSED |
| `test_analytics_security.py` | 7 tests | Role-based access control, operator denial, SQL injection defense, path traversal defense. | ✅ PASSED |
| `test_analytics_reconciliation.py` | 2 tests | Event count reconciliation, excluded event tracking, data quality status flags. | ✅ PASSED |
| `test_analytics_concurrency.py` | 2 tests | Concurrent summary queries and multi-threaded audit logging under load. | ✅ PASSED |

**Total Phase 13 Backend Tests: 49 / 49 PASSED (100%)**
**Full Backend Regression: 336 / 336 PASSED (100%)**

---

## 3. Frontend Playwright E2E Suite (`apps/web/e2e/analytics-dashboard.spec.ts`)

| Test ID | Test Scenario | Verified Invariants | Status |
| :--- | :--- | :--- | :---: |
| `TC-ANA-01` | Dashboard route loads | Prominent non-predictive governance watermark displayed. | ✅ PASSED |
| `TC-ANA-02` | Role switcher | Simulating `OPERATOR` role triggers 403 access-denied banner. | ✅ PASSED |
| `TC-ANA-03` | Filter bar | District and period dropdowns switch values and trigger updates. | ✅ PASSED |
| `TC-ANA-04` | KPI strip | Overview KPI cards render observed counts and trend badges. | ✅ PASSED |
| `TC-ANA-05` | Call volume trends | Accessible bar visualizer and table view toggle render. | ✅ PASSED |
| `TC-ANA-06` | Safety & SVI distributions | Deterministic percentages and band distributions render. | ✅ PASSED |
| `TC-ANA-07` | Language & service demand | Multilingual demand and service categories render. | ✅ PASSED |
| `TC-ANA-08` | Follow-up & operator workload | Completion rates and counselor workload metrics render. | ✅ PASSED |
| `TC-ANA-09` | Small-cell suppression | Selecting `PY-KKL` renders `SUPPRESSED` badge without raw count leakage. | ✅ PASSED |
| `TC-ANA-10` | Metric Inspector drawer | Clicking KPI opens inspector showing formula, trust level, version. | ✅ PASSED |
| `TC-ANA-11` | Operator workstation link | Operator `/calls` top bar includes `Operations Analytics` navigation link. | ✅ PASSED |

**Total Phase 13 E2E Tests: 22 tests across Desktop & Mobile Chrome (100% pass rate)**

---

## 4. Edge Cases & Attack Surface Coverage

### 4.1 Difference & Subtraction Attacks
- **Vulnerability**: If an adversary knows District Total = 12, Category A = 10, and Category B is suppressed ($<10$), they can derive $12 - 10 = 2$.
- **Mitigation Tested**: When exactly 1 cell is suppressed in a distribution, the second smallest cell is also suppressed (complementary suppression), preventing algebraic derivation.

### 4.2 Re-Identification via Low-Volume Spikes
- **Vulnerability**: A real-time spike in an obscure district could reveal an active caller.
- **Mitigation Tested**: Real-time micro-bursts are buffered and reported over closed reporting periods (e.g. daily/weekly), avoiding correlating live calls with dashboard numbers.

### 4.3 Input Sanitization & IDOR
- **Vulnerability**: Malformed district parameters containing `' OR 1=1;--` or `../etc/passwd`.
- **Mitigation Tested**: `normalize_district()` detects suspect characters and safely maps the request to `UNKNOWN`, preventing SQL injection or filesystem traversal.
