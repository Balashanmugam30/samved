# SAMVED Security Incident Response Plan (SOP)

## 1. Incident Classification
- **SEV-1 (Critical)**: Active PII data breach, unauthenticated remote code execution, denial of live telephony service, broken cryptographic audit chain.
- **SEV-2 (High)**: Bypass of district isolation boundaries (IDOR), unauthorized escalation override, repeated brute force volumetric attacks.
- **SEV-3 (Medium)**: PII scrubber regex false negative in non-public logs, isolated WebSocket connection flooding.
- **SEV-4 (Low)**: Minor policy discrepancy, non-critical documentation or header warning.

## 2. Response Procedures
1. **Identification**: Alert triggered by rate limiter progressive block, audit chain integrity verification failure, or supervisor report.
2. **Containment**:
   - For compromised accounts: Revoke user session token and set `is_active = FALSE` in database.
   - For malicious IP addresses: Temporary rate limiter block (`record_abuse_strike`) or edge firewall block.
   - For data leakage: Quarantine affected records and trigger immediate PII scrubber sanitization.
3. **Investigation & Integrity Audit**:
   - Run `GET /v1/security/audit/verify` to confirm ledger integrity and pinpoint any tampered entries.
   - Inspect sanitized JSON logs for request ID correlation.
4. **Remediation**: Deploy hotfix or update regex rules.
5. **Post-Mortem & Reporting**: Document root cause, affected scopes, and preventive enhancements within 24 hours.
