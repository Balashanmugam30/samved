# SAMVED Phase 15: Living Security & Governance Control Inventory

This inventory documents all 11 active security and governance controls implemented in SAMVED Phase 15.

| Control ID | Control Name | Category | Status | Description | Verification Method |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CTRL-AUTH-001** | Identity & Context Verification | AUTHENTICATION | OPERATIONAL | Verifies user identity headers, session tokens, and district context. | `test_security_auth.py` |
| **CTRL-AUTH-002** | Least Privilege RBAC | AUTHORIZATION | OPERATIONAL | Enforces 5 distinct roles with granular permissions. | `test_security_rbac.py` |
| **CTRL-AUTH-003** | Object Scope & District Isolation | AUTHORIZATION | OPERATIONAL | Prevents cross-district data leakage and unauthorized operator record modification. | `test_security_idor.py` |
| **CTRL-DATA-001** | Indian Entity PII Redaction Pipeline | DATA_PROTECTION | OPERATIONAL | Masks Aadhaar, PAN, phone numbers, emails, and bank accounts. | `test_security_pii.py` |
| **CTRL-DATA-002** | Log Stream PII Sanitization | DATA_PROTECTION | OPERATIONAL | Intercepts log records to scrub sensitive entities before emission. | `test_security_pii.py` |
| **CTRL-DATA-003** | Data Retention & Lifecycle Manager | DATA_PROTECTION | OPERATIONAL | Configurable TTL policies with supervisor-approved destructive purging. | `test_security_retention.py` |
| **CTRL-AUDT-001** | Cryptographically Chained Audit Trail | AUDITABILITY | OPERATIONAL | Append-only ledger chained with SHA-256 hashes for tamper evidence. | `test_security_audit.py` |
| **CTRL-ABUS-001** | Sliding-Window Adaptive Rate Limiter | ABUSE_RESISTANCE | OPERATIONAL | Protects public endpoints, telephony ingresses, and API routes. | `test_security_rate_limiting.py` |
| **CTRL-ABUS-002** | WebSocket Frame & Message Rate Guard | ABUSE_RESISTANCE | OPERATIONAL | Restricts WebSocket frames to <= 64KB and limits throughput to 10 msg/s. | `test_security_websocket.py` |
| **CTRL-GOVN-001** | Synthetic Simulation Quarantine | GOVERNANCE | OPERATIONAL | Isolates synthetic evaluation runs from mutating production case records. | `test_security_idor.py` |
| **CTRL-GOVN-002** | Zero Autonomous Dispatch Guardrail | GOVERNANCE | OPERATIONAL | Architectural constraint requiring human supervisor confirmation for emergency dispatch. | `test_orchestration_safety.py` |
