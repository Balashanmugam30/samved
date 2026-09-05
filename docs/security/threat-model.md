# SAMVED Security Threat Model (STRIDE Framework)

## 1. Threat Profile
SAMVED operates in a high-stakes public-service helpline environment (NHAA 14566). Attackers may range from curious callers and distressed individuals to malicious perpetrators attempting to compromise victim safety or disrupt operations.

| Threat Category (STRIDE) | Attack Vector | System Impact | Mitigation in Phase 15 |
| :--- | :--- | :--- | :--- |
| **Spoofing Identity** | Attacker impersonates a supervisor or district admin via forged headers or stolen tokens. | Unauthorized case alteration, illegitimate escalation overrides. | Role extraction & header context validation (`CTRL-AUTH-001`), OIDC integration ready. |
| **Tampering with Data** | Attacker alters past case notes, SVI risk scores, or audit logs to conceal misconduct. | Loss of evidentiary integrity, inaccurate victim triage. | Cryptographically chained SHA-256 audit ledger (`CTRL-AUDT-001`), append-only design. |
| **Repudiation** | Operator or supervisor denies overriding a critical emergency escalation recommendation. | Lack of accountability in high-stakes public service. | Verifiable provenance recorded with actor ID, timestamp, and signature in audit logs. |
| **Information Disclosure** | Caller PII (Aadhaar, PAN, phone numbers, addresses) leaked via logs, API responses, or SIEM. | Severe victim harm, stalking, harassment, regulatory breach (DPDP Act). | High-accuracy Indian PII scrubbing engine (`CTRL-DATA-001`, `CTRL-DATA-002`) across logs & text. |
| **Denial of Service** | Volumetric flooding of telephony webhooks, WebSocket frame bombardment, or rapid API calls. | Service outage preventing victims from reaching helpline operators. | Sliding window rate limiter (`CTRL-ABUS-001`), 64KB WebSocket frame bounds (`CTRL-ABUS-002`). |
| **Elevation of Privilege** | District Admin queries case records outside their assigned district; Operator triggers purge. | Insecure Direct Object Reference (IDOR), unauthorized cross-jurisdiction data access. | Object-level scope validation & district boundary isolation (`CTRL-AUTH-003`, `CTRL-AUTH-002`). |

## 2. Inviolable Safety Guardrails
- **Human Authority**: The AI model cannot dispatch emergency units or initiate follow-up outreach without explicit human confirmation.
- **Simulation Quarantine**: Synthetic scenario replays cannot mutate production databases (`CTRL-GOVN-001`).
