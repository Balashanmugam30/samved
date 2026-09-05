# SAMVED Security & Privacy: Prototype Limitations & Production Readiness

## 1. Explicit Non-Goals & Prototype Scope
SAMVED Phase 15 provides prototype security hardening suitable for developer evaluation, demonstrations, and SIH benchmarking.
To maintain absolute honesty and eliminate "security theater", the following limitations are explicitly documented:

| Capability | Current Phase 15 Prototype State | Production Requirement (Phase 16+) |
| :--- | :--- | :--- |
| **Authentication & Tokens** | Role & identity headers (`X-User-Role`, `X-User-Id`) with simulated Bearer token parsing. | OIDC / OAuth 2.0 identity provider (Keycloak / Azure AD / Auth0) with JWT signature validation. |
| **Data Encryption at Rest** | PostgreSQL column-level schemas and JSONB attributes. | Cloud KMS or Hardware Security Module (HSM) encryption with envelope keys (AES-256-GCM). |
| **Transport Layer Security** | Plaintext HTTP/WS in local dev environment; container ports exposed internally. | TLS 1.3 edge termination via NGINX/Envoy or AWS ALB with strict HSTS and cert rotation. |
| **Rate Limiting** | Thread-safe, in-memory sliding window rate limiter per container instance. | Distributed Redis cluster backing sliding window rate limits across auto-scaled pods. |
| **Audit Ledger Storage** | In-memory append-only list backed by PostgreSQL `audit_logs` table. | Cloud immutable WORM storage (e.g. AWS S3 Object Lock or Azure Immutable Blob) with external notary. |
| **Penetration Testing** | Automated pytest security regression tests and Playwright browser checks. | Independent third-party CERT-In empanelled security audit and dynamic DAST scanning. |

## 2. Ethical & Human Safeguards
1. **Never Autonomous**: SAMVED never initiates legal action, emergency service dispatch, or law enforcement reporting autonomously.
2. **Never a Lie Detector**: Acoustic stress signals and vocal tremor indicators are non-diagnostic operational cues to guide empathetic operator responses, not evidence of credibility or deception.
3. **Never Punitive**: System records cannot be used to penalize helpline operators for prioritizing victim safety over call handling duration targets.
