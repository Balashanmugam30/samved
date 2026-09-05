# Operational Runbook: Follow-up Workflows & Continuity Engine (Phase 12)

## 1. Purpose & Guiding Principles
This runbook guides tele-counselors, supervisors, and platform administrators on managing safe, human-supervised follow-up actions for domestic violence and harassment cases handled through NHAA 14566.

### Guiding Principles:
- **No Autonomous Outbound Dialing**: The platform will never trigger automated outbound phone calls or robot voicemails. All callbacks are placed manually by an authorized tele-counselor.
- **Safety First**: If a caller is in acute crisis or danger (`CRITICAL` safety state), immediate emergency handoff protocols must be executed. Follow-up scheduling cannot substitute for acute emergency intervention.
- **Strict Safe Contact Windows**: Never contact a caller outside their agreed-upon safe contact window (e.g., while an abuser is present).
- **Consent Precedence**: If a caller requests not to be contacted or revokes consent, all contact attempts must halt immediately.

---

## 2. Operator Workflows

### 2.1 Scheduling a Safe Follow-up Task
1. Navigate to the active call session in the **Workstation Console** (`/calls`).
2. Locate the **Follow-up Workqueue & Continuity Engine** panel.
3. Click the **"+ Schedule Follow-up"** button to open the creation modal.
4. Select the appropriate **Follow-up Type**:
   - `CHECK_IN`: Welfare or safety check-in.
   - `HUMAN_CALLBACK`: Scheduled counselor callback.
   - `RESOURCE_FOLLOW_UP`: Providing or verifying shelter/legal aid info.
   - `CASE_REVIEW`: Internal multidisciplinary team review.
   - `DOCUMENT_FOLLOW_UP`: Reviewing safety plan or legal petition docs.
   - `HANDOFF_FOLLOW_UP`: Transition to local protection officer or NGO.
   - `OPERATOR_REVIEW`: Supervisor or quality review.
5. Set the **Priority** (`LOW`, `NORMAL`, `HIGH`, `CRITICAL_REVIEW`).
6. Enter a clear, clinical **Purpose** (e.g., "Verify arrival at shelter and provide Protection Officer contact").
7. Select the **Contact Channel** (`OPERATOR_CALLBACK`, `PHONE`, `SMS`, `INTERNAL_TASK`).
8. Specify the caller's explicit **Safe Contact Window** (e.g., `09:00-12:00`).
9. Verify that **Human Tele-Counselor Only** is checked.
10. Click **"Schedule Follow-up"**. The task will appear in the workqueue and link automatically to the Case Knowledge Graph.

---

### 2.2 Executing and Recording a Follow-up Attempt
1. In the Workqueue, filter by **"Ready"** or **"Scheduled"**.
2. Click **"Start Task"** on the target follow-up card. The status transitions to `IN_PROGRESS`.
3. Verify that the current system time falls within the caller's **Safe Window**.
4. Conduct the phone outreach or internal task manually.
5. In the task card, click **"Record Attempt"**:
   - Select the channel used.
   - Choose the contact result:
     - `CONTACTED_SUCCESSFULLY`: Reached the caller safely.
     - `NO_ANSWER`: No answer; do NOT leave voicemail unless explicitly approved in contact preferences.
     - `CALLER_DECLINED`: Caller is currently unable or unwilling to talk.
     - `RESCHEDULED`: Caller requested a different time.
     - `WRONG_CONTACT`: Number invalid or wrong party answered.
   - Enter concise, objective clinical notes.
   - Click **"Save Attempt Record"**.

---

### 2.3 Completing a Follow-up Task
1. When all objectives of the follow-up task have been satisfied, click **"Complete"** on the task card or within the details drawer.
2. Select the final **Outcome** (`CONTACTED_SUCCESSFULLY`, `REFERRED`, `UNRESOLVED`).
3. Click **"Mark Completed"**. The task status updates to `COMPLETED` and an immutable audit event is emitted.

---

### 2.4 Rescheduling a Follow-up Task
1. If the caller requests a different time slot or the attempt resulted in `RESCHEDULED`:
2. Click **"Reschedule"** on the card.
3. Enter the new **Target Scheduled Time** (ISO UTC).
4. Provide the reason for rescheduling (e.g., "Caller requested callback after 18:00").
5. Click **"Confirm Reschedule"**. The task returns to `SCHEDULED` status.

---

### 2.5 Caller Consent Revocation (Immediate Emergency Stop)
If at any point the caller states they do not want further contact, or withdraws consent:
1. Click the red **"Revoke Consent"** button on the task card or in the Details Drawer.
2. Confirm the action.
3. **Automated Impact**:
   - The case consent state transitions to `REVOKED`.
   - All pending, scheduled, and in-progress follow-up tasks for that case are immediately transitioned to `BLOCKED`.
   - Further task creation with outbound contact channels is strictly blocked by the deterministic policy layer.
   - An immutable `FOLLOWUP_CONSENT_REVOKED` event is logged to the system audit trail.

---

## 3. Auditing & Compliance
- To view the audit history for a specific task: Click **"Audit"** on the task card.
- To view the global follow-up audit trail: Click **"Audit Trail"** in the workqueue header.
- Every state transition, attempt, rescheduling, and consent revocation is cryptographically timestamped with operator ID and immutable event payloads.
