# SAMVED — Security, Privacy & Confidentiality Architecture

## 1. Domain Sensitivity & Ethical Responsibility
The National Toll-Free Drug De-Addiction Helpline (NHAA 14566) interacts with vulnerable citizens in acute distress, seeking confidential support regarding substance use and rehabilitation. Security and confidentiality are therefore fundamental architectural safeguards rather than superficial features.

---

## 2. Core Security Invariants

### 1. Zero Committed Secrets
- All environment configurations rely strictly on runtime variables loaded via `.env`.
- `.gitignore` rigorously prevents accidental inclusion of `.env`, `.env.*.local`, `.pem`, and certificate keys.
- Continuous integration verifies that no secret patterns exist in staged code.

### 2. PII Masking & Data Minimization
- Caller phone numbers are masked at the telephony ingress boundary (e.g. `+91-XXXXX-12345`).
- Names, home addresses, and employer details must not be written to unstructured application logs.
- The structured logging formatter scrubs all keys matching `authorization`, `token`, `secret`, `caller_number`, and `raw_audio`.

### 3. Ephemeral Audio Streams
- Live audio frames streamed from Exotel are processed in-memory.
- In `DEV` and `SIMULATION` modes, raw audio is never written to disk.
- In `LIVE` operational mode, audio retention policies strictly require informed consent and adherence to MoSJE statutory guidelines.

### 4. Deterministic Safety Boundaries
- Generative AI models are strictly prohibited from making autonomous decisions regarding emergency medical dispatch, legal accusations, or law enforcement contact.
- Safety policies trigger human operator review with transparent explanation factors.

---

## 3. PII Redaction Architecture (Phase 15 Target)
In Phase 15, SAMVED integrates a specialized Indian-entity redaction engine (utilizing Microsoft Presidio and IndicNER models) to automatically sanitize transcripts of names, Aadhaar numbers, and localized landmarks before longitudinal persistence.
