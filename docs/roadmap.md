# SAMVED — Multi-Phase Engineering Roadmap

| Phase | Milestone | Scope & Deliverables | Status |
| :---: | :--- | :--- | :---: |
| **0** | **Engineering Foundation** | Monorepo layout, Next.js web shell, FastAPI backend, Event contracts (v1.0), Provider abstractions, Test suite, Playwright validation, CI/CD, and Git setup. | **COMPLETE** |
| **1** | **Telephony & Media Ingress** | Exotel bidirectional audio streaming integration (8kHz PCM) over WebSockets, call state machine, session manager, and diagnostic simulator. | **COMPLETE** |
| **2** | **Multilingual Speech & Reasoning** | Sarvam real-time STT (`saaras:v3`), Google Gemini (`gemini-2.5-flash`) conversational intelligence, Sarvam Bulbul TTS (`bulbul:v3`) voice synthesis pipeline, barge-in interruption. | **COMPLETE** |
| **3** | **Realtime Transcripts & Operator Console** | Dedicated `/ws/operator` event channel, dynamic subscriptions (`SUBSCRIBE_CALL`), REST snapshot APIs (`/v1/calls`), Master-Detail operator console with live partial/final transcripts, timeline filtering, payload inspector, and localhost runbook. | **COMPLETE** |
| **4** | **Deterministic Safety Engine** | High-priority safety rules, immediate physical threat detection, self-harm keywords, supervisor alert dispatch. | ⏳ Next |
| **5** | **Stress Vulnerability Index (SVI)** | Explainable 0–100 vulnerability index scoring engine with 4 calibrated prototype bands and contributing factor breakdown. | ⏳ Scheduled |
| **6** | **Acoustic Signal Processing** | Non-verbal paralinguistic feature extraction (pitch, jitter, shimmer, speaking rate, silence ratio) as supporting triage evidence. | ⏳ Scheduled |
| **7** | **Adaptive Multilingual Dialogue** | Code-switching handling, empathetic pacing, clarification turns, conversational repair. | ⏳ Scheduled |
| **8** | **Human Operator Console** | Full-fledged tele-counselor workstation with warm call transfer, manual SVI overrides, and live counseling notes. | ⏳ Scheduled |
| **9** | **Multi-Agent Orchestration** | Specialized bounded agents (Safety, Legal, Care, Case, Follow-up, Governance) with state graph coordination. | ⏳ Scheduled |
| **10** | **Grounded Legal & Scheme RAG** | Official gazette RAG (NDPS Act, Mental Healthcare Act, MoSJE NAPDDR IRCA database) with strict citation verification. | ⏳ Scheduled |
| **11** | **Case Intelligence & History** | Longitudinal anonymous case timelines, intake records, referral recommendations, and multi-session tracking. | ⏳ Scheduled |
| **12** | **Follow-up & Care Continuity** | Automated check-in cadences, appointment reminders, and counselor follow-up task queues. | ⏳ Scheduled |
| **13** | **Operational Helpline Analytics** | Aggregated call volumes, SVI severity heatmaps, geographic clustering, and administrative reports for MoSJE. | ⏳ Scheduled |
| **14** | **Scenario Simulation Engine** | Automated synthetic scenario benchmark suite, WER evaluation, high-risk recall verification, and operator training sandbox. | ⏳ Scheduled |
| **15** | **Security & Privacy Hardening** | PII redaction pipeline (Presidio/IndicNER), cryptographic consent logs, role-based access control, and immutable audit trails. | ⏳ Scheduled |
| **16** | **Deployment & SIH Finalization** | High-availability deployment, automated failover, load testing, comprehensive documentation, and SIH 2026 presentation readiness. | ⏳ Scheduled |
