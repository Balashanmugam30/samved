# Security & Privacy Policy

## 1. Scope and Mission
SAMVED is designed as an AI-assisted victim triage, vulnerability assessment, and response intelligence layer for the National Toll-Free Drug De-Addiction Helpline (NHAA 14566). Given the sensitive nature of victim communications, security, privacy, and confidentiality are first-class architectural constraints.

## 2. Core Security & Privacy Principles
1. **Zero Committed Secrets**:
   - No API keys, credentials, private certificates, or tokens may ever be committed to git.
   - All environments must load credentials via environment variables (`.env`).
   - `.env.example` must contain only dummy templates.
2. **Data Minimization & Confidentiality**:
   - PII (Personally Identifiable Information) such as caller phone numbers, personal names, and physical addresses must never be written to unstructured logs or unencrypted persistent storage.
   - Audio recordings are ephemeral by default in development/test runs and require explicit retention and consent policies in operational modes.
3. **Deterministic Safety Primacy**:
   - The safety engine operates on deterministic policies and auditable rules.
   - Generative LLM responses must never bypass deterministic safety checks or make autonomous emergency dispatch decisions.
4. **Role-Based Access Control (RBAC)**:
   - Operators, supervisors, and system administrators have distinct, auditable permission boundaries.
5. **Human-in-the-Loop Oversight**:
   - High-stakes workflows (such as emergency escalation recommendations or referral triggers) require human operator confirmation and support human override.

## 3. Vulnerability Reporting
If you identify any security flaw, vulnerability, or accidental secret exposure:
- **Do not file a public GitHub issue.**
- Email the project maintainers directly with reproduction steps.
- Provide sufficient details to verify and remediate the vulnerability.
- Maintainers will acknowledge within 48 hours and coordinate remediation.
