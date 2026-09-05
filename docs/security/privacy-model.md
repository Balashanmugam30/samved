# SAMVED Privacy & Data Protection Model

## 1. Compliance Principles
SAMVED adheres to the Digital Personal Data Protection Act (DPDP Act, India) and international best practices for victim protection:
1. **Data Minimization**: Only collect data essential for crisis triage, risk assessment, and referral support.
2. **Purpose Limitation**: Caller data is used strictly for immediate victim assistance and operational quality improvement.
3. **Storage Limitation**: Raw audio is retained for the minimum duration necessary (default 30 days) and purged or anonymized.
4. **No Re-identification**: Aggregated district analytics enforce cell suppression ($k \ge 5$) to prevent victim re-identification.

## 2. Indian Entity PII Redaction Pipeline
All inbound transcripts and outbound log streams pass through `PIIScrubber` before storage or presentation to operators.

### Redaction Rules
- **Aadhaar Numbers**: First 8 digits masked, preserving last 4 digits for optional caller verification: `[REDACTED_AADHAAR:XXXX-XXXX-1234]`.
- **PAN Cards**: Masked preserving first 2 letters and trailing checksum: `[REDACTED_PAN:ABXXXXXF]`.
- **Indian Mobile Numbers**: Country code preserved, prefix masked: `[REDACTED_PHONE:+91-XXXXX-1234]`.
- **Bank Accounts**: Preceded by account keywords (`a/c`, `account no`): `A/C [REDACTED_ACCOUNT:XXXX1234]`.
- **Email Addresses**: Fully redacted: `[REDACTED_EMAIL]`.
- **Vehicle Numbers**: Formatted registration numbers: `[REDACTED_VEHICLE]`.

## 3. Data Retention Lifecycles
| Data Category | Retention Period | Purge Strategy | Supervisor Approval Required |
| :--- | :--- | :--- | :--- |
| **Raw Audio Recordings** | 30 Days | HARD_DELETE | Yes |
| **Call Transcripts** | 90 Days | ANONYMIZE | Yes |
| **Analytics Aggregates** | 365 Days | ANONYMIZE | No |
| **Audit Trail Logs** | 730 Days | ARCHIVE_COLD | Yes |
| **Training Run Artifacts** | 180 Days | HARD_DELETE | No |
