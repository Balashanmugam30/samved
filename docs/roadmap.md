# SAMVED — Multi-Phase Engineering Roadmap

| Phase | Milestone | Scope & Deliverables | Status |
| :---: | :--- | :--- | :---: |
| **0** | **Engineering Foundation** | Monorepo layout, Next.js web shell, FastAPI backend, Event contracts (v1.0), Provider abstractions, Test suite, Playwright validation, CI/CD, and Git setup. | **COMPLETE** |
| **1** | **Telephony & Media Ingress** | Exotel bidirectional audio streaming integration (8kHz PCM) over WebSockets, call state machine, session manager, and diagnostic simulator. | **COMPLETE** |
| **2** | **Multilingual Speech & Reasoning** | Sarvam real-time STT (`saaras:v3`), Google Gemini (`gemini-2.5-flash`) conversational intelligence, Sarvam Bulbul TTS (`bulbul:v3`) voice synthesis pipeline, barge-in interruption. | **COMPLETE** |
| **3** | **Realtime Transcripts & Operator Console** | Dedicated `/ws/operator` event channel, dynamic subscriptions (`SUBSCRIBE_CALL`), REST snapshot APIs (`/v1/calls`), Master-Detail operator console with live partial/final transcripts, timeline filtering, payload inspector, and localhost runbook. | **COMPLETE** |
| **4** | **Deterministic Safety Engine** | Explicit versioned safety rules (v1), sub-5ms deterministic evaluation, Unicode NFC normalization, clause-isolated negation check, compound weapon escalation, operator oversight banner, audit acknowledgment trail, and interactive Safety Lab. | **COMPLETE** |
| **5** | **Stress Vulnerability Index (SVI)** | Explainable 0–100 vulnerability index scoring engine with 4 calibrated prototype bands, temporal recency weighting, protective factor bounds, feature attribution, operator SVI panel, and interactive SVI Simulation Lab. | **COMPLETE** |
| **6** | **Acoustic Signal Processing** | Deterministic paralinguistic and telephony quality analysis (pitch 80–350Hz, speech ratio, silence, energy variability, clipping) as supporting triage evidence, operator Acoustic Panel, and Simulation Lab. | **COMPLETE** |
| **7** | **Adaptive Conversation Engine** | Deterministic conversational policy layer, strict priority hierarchy (P0–P5), information-gap planning, bounded repetition, contradiction handling, operator overrides, multilingual localized templates, operator Adaptive Panel, and Simulation Lab. | **COMPLETE** |
| **8** | **Human Operator Console & Workstation** | Full-fledged tele-counselor workstation with human takeover, pause/resume, safety checks, multi-stage handoff, structured notes, unified call triage summary, and audit timeline. | **COMPLETE** |
| **9** | **Multi-Agent Orchestration** | Bounded specialized AI workers (Safety, Acoustic, Language, Context, Briefing, Support stub) with deterministic DAG coordination, latency budgeting, and operator briefings. | **COMPLETE** |
| **10** | **Grounded Legal & Scheme RAG** | Official gazette RAG (NDPS Act, Mental Healthcare Act, MoSJE NAPDDR IRCA database) with strict citation verification. | ⏳ Next |
| **11** | **Case Intelligence & History** | Longitudinal anonymous case timelines, intake records, referral recommendations, and multi-session tracking. | ⏳ Scheduled |
| **12** | **Follow-up & Care Continuity** | Automated check-in cadences, appointment reminders, and counselor follow-up task queues. | ⏳ Scheduled |
| **13** | **Operational Helpline Analytics** | Aggregated call volumes, SVI severity heatmaps, geographic clustering, and administrative reports for MoSJE. | ⏳ Scheduled |
| **14** | **Scenario Simulation Engine** | Automated synthetic scenario benchmark suite, WER evaluation, high-risk recall verification, and operator training sandbox. | ⏳ Scheduled |
| **15** | **Security & Privacy Hardening** | PII redaction pipeline (Presidio/IndicNER), cryptographic consent logs, role-based access control, and immutable audit trails. | ⏳ Scheduled |
| **16** | **Deployment & SIH Finalization** | High-availability deployment, automated failover, load testing, comprehensive documentation, and SIH 2026 presentation readiness. | ⏳ Scheduled |
