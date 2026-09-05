# District Intelligence & Operational Analytics Runbook

## 1. Purpose & Scope
This runbook guides national helpline administrators, regional district coordinators, and operations supervisors in utilizing and managing the SAMVED Phase 13 District Intelligence & Operational Analytics subsystem for NHAA 14566.

---

## 2. Accessing the Analytics Dashboard

### 2.1 Web Interface
1. Log in to the SAMVED Operational Console.
2. Navigate to `/analytics` via the sidebar (`Analytics & Trends`) or via the top header bar in the Operator Workstation (`Operations Analytics`).
3. The dashboard automatically defaults to the national or assigned district overview in `Asia/Kolkata` time.

### 2.2 Roles & Access Permissions
- **`DISTRICT_ADMIN`**: Can review district-specific aggregates, language demand, and follow-up completion rates.
- **`SUPERVISOR`**: Can review operational team workload, response times, and access audit logs.
- **`SYSTEM_ADMIN`**: Has full cross-district visibility, can trigger batch recomputations, and inspect access logs.
- **`OPERATOR`**: Explicitly restricted from macro district intelligence. Live counselors handle individual calls in `/calls`.

---

## 3. Interpreting Metrics & Trust Classifications

Every metric carries an explicit trust classification:
- **`OBSERVED`**: Direct event count (e.g. Total Calls, Completed Calls, Unique Cases).
- **`CALCULATED`**: Mathematical formula output (e.g. Average Response Time, Completion Rate).
- **`ESTIMATED`**: Smoothed historical trend indicator.
- **`SUPPRESSED`**: Cohort $< 10$ records. Hidden to guarantee caller confidentiality.
- **`UNAVAILABLE`**: Data could not be computed due to upstream sensor outage.

> [!WARNING]
> **Non-Predictive Policy**:
> District metrics indicate helpline operational capacity and demand. Under NO circumstances should these metrics be used to infer individual victim behavior, judge neighborhood criminal risk, or trigger law enforcement actions.

---

## 4. Handling Small-Cell Suppression
When a district has fewer than 10 records for a given metric:
- The UI displays `SUPPRESSED`.
- Hovering or clicking opens the Metric Inspector, which explains: *"This metric is hidden because the reporting group is too small (<10 records) to preserve caller privacy."*
- Do not attempt to reverse-calculate suppressed values through sub-category addition.

---

## 5. Triggering Batch Recomputation
If late events arrive (e.g. offline follow-up logs from field coordinators):
1. Ensure your role is `SUPERVISOR` or `SYSTEM_ADMIN`.
2. Click the **`Recompute`** button on the filter bar.
3. The system executes a deterministic batch reconciliation job, deduplicating events by `event_id` and refreshing materialized summaries.
4. If discrepancies exceed 5%, a `DATA QUALITY DEGRADED` banner will appear until reconciliation completes.

---

## 6. Access Audit Review
To inspect who has accessed district summaries:
1. Click **`Access Audit`** on the top filter bar.
2. The modal displays a chronological log of actor IDs, roles, accessed district codes, endpoints, and timestamps.
3. All access requests are permanently archived in `analytics_access_audit`.
