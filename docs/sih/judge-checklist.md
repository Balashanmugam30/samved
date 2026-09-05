# SAMVED — SIH 2026 Judge & Evaluator Checklist

**Smart India Hackathon 2026 | PS-26093**  
**Project:** SAMVED (AI-Assisted Multilingual Emergency Triage & Operator Intelligence)  
**Version:** `1.0.0-sih2026`  

---

## 1. Quick Technical Reference for Evaluators

| Feature Area | Implementation in SAMVED | Where to Inspect in Codebase |
|---|---|---|
| **Code-Switching ASR** | Conformer & Sarvam Indic pipeline supporting Tamil, Hindi, Telugu, and English code-switching with word-level confidence. | `apps/api/app/providers/sarvam_stt.py`<br>`apps/api/app/simulation/` |
| **Acoustic Distress Detection** | Non-verbal acoustic feature extraction: f0 pitch tremor, energy variability, speech rate decay (0.0 to 1.0 stress index). | `apps/api/app/acoustic/`<br>`apps/api/app/api/v1/acoustic.py` |
| **Statistical Vulnerability Index (SVI)** | Deterministic 0–100 composite index with calibrated multimodal factor weights and band classification (Low, Mod, High, Critical). | `apps/api/app/svi/`<br>`apps/api/app/api/v1/svi.py` |
| **Human-in-the-Loop Governance** | Enforced requirement: zero autonomous dispatch; tele-counselor supervisor confirmation required for emergency vehicle dispatch. | `apps/api/app/core/config.py`<br>`apps/web/src/app/calls/` |
| **Grounded Indian Statutory RAG** | Indexed statutory knowledge: PWDVA 2005 (Sec 12, 18), ERSS 112 SOPs, MoSJE IRCA de-addiction hubs, Sakhi One Stop Centres. | `apps/api/app/knowledge/`<br>`apps/api/app/api/v1/knowledge.py` |
| **Tamper-Evident Audit Logging** | Append-only SHA-256 Merkle chain recording every triage decision, user override, and PII redaction event with non-repudiation. | `apps/api/app/security/audit.py`<br>`apps/web/src/app/audit/` |
| **Indian PII Redaction** | Heuristic & regex scrubbing for 12-digit Aadhaar, 10-digit PAN, Indian mobile numbers (+91), email addresses, and bank accounts. | `apps/api/app/security/pii.py`<br>`apps/web/src/app/security/` |
| **Fault Isolation & Resilience** | Thread-safe in-memory `CircuitBreaker` protecting all external dependencies with automated fast-fail and cooldown resets. | `apps/api/app/core/circuit.py`<br>`apps/web/src/app/operations/` |
| **Container & Cloud Orchestration** | Docker Compose multi-container setup, Kubernetes `/healthz`, `/ready`, and `/health/startup` probes. | `docker-compose.yml`<br>`apps/api/app/api/v1/health.py` |

---

## 2. Anticipated Judge Questions & Technical Answers

### Q1: "What prevents the AI from dispatching police or ambulance to a false alarm?"
> **Answer:** **Autonomous dispatch is prohibited by architectural design.** The platform contains hard programmatic guardrails: `P0_EMERGENCY_DISPATCH_ASSIST` produces a **structured dispatch recommendation** accompanied by a 3-point briefing note on the human supervisor's screen. The physical dispatch API requires explicit human operator biometric/credential confirmation (`operator_dispatch_confirm`). The AI cannot execute dispatch independently.

### Q2: "How does the system prevent LLM hallucinations during high-stakes counseling?"
> **Answer:** SAMVED does not allow open-ended, free-form generative LLMs to dictate emergency advice. All statutory protections, helpline numbers, and legal citations are grounded using vector-indexed Indian statutes (PWDVA 2005, ERSS 112 SOPs). When high distress is detected, the adaptive engine restricts the LLM prompt space to vetted de-escalation micro-templates and factual grounding instructions.

### Q3: "How does the system handle poor network quality or an external API outage?"
> **Answer:** Every external service (Sarvam, Gemini, Exotel, Redis) is protected by a dedicated **Circuit Breaker**. If Sarvam STT experiences latency spikes exceeding the failure threshold (5 consecutive timeouts), the circuit immediately trips to `OPEN`. The call pipeline fast-fails into local fallback processing (pre-packaged offline Conformer/Whisper models) without hanging the active call or causing audio drops.

### Q4: "How is victim privacy and DPDP Act compliance ensured?"
> **Answer:** Data minimization is enforced at both client and server layers. Transcribed audio is passed through the `IndianPIIRedactor` which masks 12-digit Aadhaar numbers (`XXXX-XXXX-1234`), PAN cards, and contact numbers before writing to databases or logging into the cryptographically hashed audit chain.

---

## 3. Evaluation Scoring Rubric Alignment

| SIH Evaluation Parameter | Maximum Marks | SAMVED Capability Evidence |
|---|---|---|
| **Relevance & Need Alignment** | 20 | Directly addresses real-world challenges of NHAA 14566 and ERSS 112: language barriers, emotional panic, and tele-counselor burnout. |
| **Technical Breadth & Execution** | 25 | 16-phase comprehensive full-stack implementation: FastAPI, Next.js 14, WebSockets, PostgreSQL, Redis, PyTorch/Sarvam, Docker, Circuit Breakers. |
| **Verification & Testing** | 20 | **629 Automated Tests** (429 backend unit/contract + 200 Playwright E2E browser tests) with 100% pass rate in CI. |
| **User Experience & Demonstration** | 15 | Dedicated SIH Presentation Demo Hub (`/demo`) with 1-click Tamil/English code-switching replay and Operations Console (`/operations`). |
| **Safety, Ethics & Governance** | 20 | Human-in-the-loop validation, Indian PII scrubbing, tamper-evident SHA-256 Merkle chain, zero legal guilt claims. |
