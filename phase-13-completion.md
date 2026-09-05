# SAMVED Phase 13 — District Intelligence & Operational Analytics
**Privacy-Preserving, Explainable, Non-Predictive, Human-Supervised**

## Repository
- **Repository**: https://github.com/Balashanmugam30/samved
- **Branch**: `main`
- **Milestone**: Phase 13 — District Intelligence & Operational Analytics
- **Target Helpline**: National Drug De-Addiction Helpline (**NHAA 14566**), Ministry of Social Justice and Empowerment (MoSJE), Government of India
- **Problem Statement ID**: Smart India Hackathon 2026 (Problem Statement 26093)

---

## Metric Catalog
- **Catalog Version**: `v1.0.0`
- **Metric Definitions**: 17 standardized operational metrics across Volume, Safety, SVI, Language, Operator, Follow-up, Knowledge, and System categories.
- **Trust Classifications**:
  - `OBSERVED`: Direct event counts (`calls_received`, `calls_completed`, `unique_case_count`, `active_followups`, `human_takeovers_count`, `knowledge_queries`).
  - `CALCULATED`: Deterministic mathematical formulas (`average_response_time_sec`, `followup_completion_rate`, `safety_state_distribution`, `svi_band_distribution`, `average_svi`).
  - `ESTIMATED`: Smoothed historical capacity indicators.
  - `SUPPRESSED`: Low-cohort metrics hidden to protect confidentiality ($k < 10$).
  - `UNAVAILABLE`: Data degraded by external sensor/network interruptions.

---

## Aggregation
- **Ingress Event Deduplication**: Unique tracking by `event_id` in `EventAggregator` preventing duplicate counting.
- **Materialized Summary Models**: Precomputed periodic summaries in `analytics_district_summaries` and multi-dimensional metric values in `analytics_metric_values`.
- **Late Event Handling**: Bounded batch recomputation refreshes affected historical periods without corrupting existing totals.
- **Data Quality Indicators**: Tracking `source_event_count`, `processed_count`, and `excluded_count`, triggering `DATA QUALITY DEGRADED` warning if exclusion ratio exceeds 5%.

---

## Privacy
- **K-Anonymity Threshold**: Default $k = 10$ records. Any group, cell, or district with fewer than 10 records is automatically suppressed.
- **Raw Count Scrubbing**: When suppressed, `raw_value` is set to `null` and `display_value` is replaced with `"SUPPRESSED"`, preventing API serialization leakage.
- **Display Rounding**: Counts $\ge 1,000$ display rounded values (e.g. `~1.2K`) for macro volume readability.
- **Zero Profiling**: Language, paralinguistics, and acoustics are strictly prohibited from being used to infer religion, caste, ethnicity, or political beliefs.

---

## Suppression
- **Small-Cell Suppression**: Validated on low-volume districts (`PY-KKL`, 6 calls), successfully suppressing all KPI counts and distributions.
- **Complementary Suppression**: Prevents difference/subtraction attacks ($Total - A = B$). If exactly one category in a distribution falls below $k$, the next smallest cell is also suppressed.

---

## District Analytics
- **Geographic Dimensions**: Bounded to State $\to$ District level.
- **Normalized Codes**: Canonical mapping table normalizing spelling variants and aliases (e.g. `TN-CHE` for Chennai/Madras, `DL-CEN` for Central/New Delhi, `MH-MUM` for Mumbai/Bombay, `KA-BLR` for Bengaluru/Bangalore, `UNKNOWN` for unstated locations).
- **Zero Coordinates**: Household maps, GPS coordinates, cell tower traces, and fine-grained street addresses are strictly prohibited.

---

## Safety Analytics
- **Deterministic Distribution**: Aggregated percentage distribution across Phase 4 deterministic safety bands: `NONE` (62.0%), `WATCH` (18.3%), `ELEVATED` (11.3%), `HIGH` (6.3%), and `CRITICAL` (2.1%).
- **Supervisor Escalations**: Tracking calls requiring counselor escalation intervention.

---

## SVI Analytics
- **Severity Band Distribution**: Calibrated distribution across Low (0–25), Moderate (26–50), High (51–75), and Critical (76–100) vulnerability bands.
- **Average SVI**: Median and average SVI scores (46.5 in Chennai baseline) informing regional psychological support resource allocation.

---

## Language Analytics
- **Multilingual Mix**: Aggregating demand across Hindi (45.8%), Tamil (31.7%), English (15.5%), and Telugu (7.0%).
- **Shift Planning**: Directly informs multilingual tele-counselor shift scheduling and language-specific hiring.

---

## Service Demand
- **Standardized Categories**: Standardized request categories (`COUNSELING_REFERRAL`, `SAFETY_SUPPORT`, `HEALTH_SUPPORT`, `LEGAL_INFORMATION`, `FOLLOW_UP`).
- **Free-Form Text Scrubbing**: Free-form dialogue is strictly excluded from district analytics dimensions.

---

## Follow-up Analytics
- **Care Continuity Metrics**: Tracking created (34), completed (28), missed (4), and consent-blocked (2) follow-ups.
- **Completion Rate**: 87.5% completion rate demonstrating counselor engagement while honoring caller consent boundaries.

---

## Operator Capacity
- **Counselor Workload**: Average calls per counselor (11.8), active counselors (12), human takeovers (18), and handoffs requested (22) vs confirmed (20).
- **Response Latency**: Median counselor intervention latency of 3.4 seconds.

---

## System Reliability
- **P95 Latency**: 28ms turn latency across REST and WebSocket gateways.
- **STT Failure Rate**: 0.4% streaming error rate under normal operating conditions.

---

## Trends
- **Deterministic Period-over-Period**: Percentage change comparison between current and previous intervals.
- **Directional Classification**: `RISING` ($\ge +5\%$), `FALLING` ($\le -5\%$), `STABLE` (within $\pm 5\%$), or `INSUFFICIENT_DATA` (cohort $< 10$).
- **Zero Machine Learning Forecasting**: No speculative neural network predictions or predictive policing models.

---

## API
Mounted at `/v1/analytics/`:
- `GET /v1/analytics/status`: Engine status, catalog version, minimum cohort threshold.
- `GET /v1/analytics/metrics`: Versioned catalog of 17 metrics.
- `GET /v1/analytics/districts`: Normalized district list.
- `GET /v1/analytics/districts/{code}/summary`: KPI card summary with privacy status.
- `GET /v1/analytics/districts/{code}/trends`: Period-over-period trend points.
- `GET /v1/analytics/districts/{code}/languages`: Multilingual demand breakdown.
- `GET /v1/analytics/districts/{code}/services`: Standardized service category demand.
- `GET /v1/analytics/districts/{code}/safety`: Safety state distribution percentages.
- `GET /v1/analytics/districts/{code}/svi`: SVI band distribution and average score.
- `GET /v1/analytics/districts/{code}/followups`: Care continuity metrics.
- `GET /v1/analytics/districts/{code}/operations`: Counselor workload and system health.
- `POST /v1/analytics/query`: Multi-dimensional bounded analytics query.
- `POST /v1/analytics/recompute`: Batch recomputation for closed periods.
- `GET /v1/analytics/audit`: Immutable access audit logs.

---

## Dashboard
- **Route**: `/analytics`
- **Watermark**: Persistent non-predictive governance banner.
- **Role Simulation**: Role switcher (`DISTRICT_ADMIN`, `SUPERVISOR`, `SYSTEM_ADMIN`, `OPERATOR`).
- **Filter Bar**: District and period selectors with K-Anonymity status tag.
- **KPI Strip**: 6 core cards with deterministic trend badges.
- **Visual Sections**: Call volume chart with table alternative toggle, Safety & SVI distributions, Language & Service demand, Follow-up workload, and Operator capacity.
- **Metric Detail Drawer**: Interactive inspector showing definition, formula, trust level, and version.

---

## Security
- **Role-Based Access Control**: `OPERATOR` role strictly forbidden (HTTP 403) from macro district intelligence.
- **IDOR Protection**: Unknown or out-of-scope districts safely normalized to `UNKNOWN`.
- **SQL & Path Traversal Injection Defense**: Suspect characters (`'`, `"`, `;`, `/`, `\`, `..`, `--`, `*`, `=`, `<`, `>`) immediately rejected to `UNKNOWN`.

---

## Audit
- **Immutable Log Store**: Every API access recorded in `analytics_access_audit` with actor ID, role, endpoint, district, and privacy outcome.
- **Supervisory Review**: Restricted to `SUPERVISOR` and `SYSTEM_ADMIN` roles.

---

## Docker
- **Docker Compose**: Validated with `docker compose config` (100% valid YAML).
- **Database Initialization**: `infra/db/init.sql` updated with 5 relational analytics tables and indexes.

---

## MCP
- **Preservation**: Docker MCP Toolkit profile `samved_dev` preserved.
- **Tooling Isolation**: MCP tools operate as local developer assistance and do not leak analytics PII.

---

## Testing
- **Backend Tests (`pytest`)**: 49 / 49 Phase 13 tests passed (100%). Full backend regression: **336 / 336 PASSED (100%)** in 9.23s.
- **Frontend E2E Tests (`playwright`)**: 22 / 22 tests passed (100%) on Desktop Chrome and Mobile Chrome. Full E2E suite: **150 / 150 PASSED (100%)**.
- **TypeScript Type Checks**: 0 errors across `@samved/schemas` and `@samved/web`.
- **Next.js Production Build**: Production build succeeded cleanly, prerendering `/analytics` (9.85 kB).

---

## Limitations
1. **No Individual Level Drill-Down**: Aggregated metrics cannot be expanded to list individual callers.
2. **Deterministic Time Buffering**: Real-time micro-bursts are buffered over reporting periods to prevent temporal re-identification.
3. **Small-Cell Hiding**: Districts with fewer than 10 calls during a period cannot display exact numbers.

---

## Governance Disclaimer
> *"District Intelligence contains aggregated operational analytics for helpline capacity planning and quality assurance. It is NOT an individual risk score, predictive policing system, offender prediction system, or basis for automated enforcement."*
