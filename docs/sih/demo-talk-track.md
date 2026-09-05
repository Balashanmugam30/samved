# SAMVED — SIH 2026 Evaluation Demo Talk-Track (3–5 Minutes)

**Target Audience:** Smart India Hackathon 2026 Judges & Technical Evaluators  
**Problem Statement:** PS-26093 — AI-Driven Multilingual Emergency Triage and Victim Support  
**Presenter Flow:** Interactive live demonstration walking through the 8-stage pipeline.

---

## Part 1: Problem Context & Governance Boundaries (0:00 – 0:45)

> *"Namaste Judges. India's emergency helplines — such as NHAA 14566 and ERSS 112 — operate under immense cognitive pressure. When a victim in distress calls, they rarely speak formal, textbook language. They code-switch between regional languages like Tamil, Hindi, Telugu, and English, whispering through tears while an aggressor is nearby.*
>
> *Existing automated systems either force callers into rigid IVR menus or rely on ungrounded black-box LLMs that hallucinate, fail on accents, or lack legal accountability.*
>
> *SAMVED changes this. SAMVED is an AI-assisted emergency triage and operator copilot built with strict human-in-the-loop governance: **zero autonomous dispatch**, **zero legal guilt claims**, and **tamper-evident cryptographic auditing**."*

---

## Part 2: The SIH Demo Hub & Flagship Replay (0:45 – 2:00)

**Action:** Open `http://localhost:3000/demo` (SIH Demo Hub).

> *"Let us open the **SIH Demo Hub**. You can see the prominent banner confirming that all caller records and scenarios on this hub are strictly synthetic test vectors to protect privacy.*
>
> *Here is our flagship evaluation scenario: `DEMO-SCENARIO-TAMIL-ENG-001`. A caller named Kavitha in Madurai is barricaded inside a room with her infant while an aggressor is actively attempting forced entry with an edged weapon.*
>
> *Notice the incoming speech turns:
> Turn 1: 'Help me please... avar romba violent-ah behave panraaru, door break panna try panraaru... enna panradhu nu therila!'
> Turn 2: 'He has a knife in hand... kaiyila kaththi vechirukaaru, threaten panraaru! Please send help, baby is crying inside room.'
>
> *Now, let's trigger the live pipeline replay with one click: **Replay Flagship Scenario**."*

**Action:** Click the **Replay Flagship Scenario** button.

---

## Part 3: Live Pipeline Execution & 8 Stages (2:00 – 3:30)

> *"In under **200 milliseconds**, all 8 micro-stages executed and verified:*
>
> 1. **Multilingual ASR:** Ingested the mixed Tamil/English audio stream, detected the `ta-en` pair, and flagged an acoustic tremor distress score of 0.94.
> 2. **Safety Rule Engine:** Zero-latency screening fired deterministic rules for weapon threat, imminent violence, and vulnerable infant presence.
> 3. **Statistical Vulnerability Index (SVI):** Computed an SVI of **88/100 (Critical Band)**. Notice that this is not an opaque number: factor weights show 35% for weapon threat, 30% for physical entry, 20% for infant co-presence, and 15% for acoustic panic.
> 4. **Adaptive Policy:** Escalated to **P0 Emergency Dispatch Assist**, modulating the counseling tone to short grounding utterances so the caller's phone does not alert the aggressor.
> 5. **Tele-Counselor Warm Transfer:** Look at this 3-point briefing box generated in less than 50ms. A human supervisor taking over does not need to read paragraphs of transcript: they immediately see the caller's barricaded state, weapon type, acoustic distress, and pre-mapped 112 dispatch advisory.
> 6. **Statutory RAG Grounding:** Retrieved verified Indian statutes — Section 12 of the Protection of Women from Domestic Violence Act (PWDVA 2005) and Madurai district IRCA / Sakhi One Stop Centre contacts.
> 7. **Case Intelligence Graph:** Automatically linked victim, child, aggressor, and weapon into a relational graph for ongoing incident tracking.
> 8. **Cryptographic Audit Seal:** The entire event was hashed using SHA-256 and appended to our Merkle audit chain with non-repudiation."*

---

## Part 4: Resilience & Operator Observability (3:30 – 4:30)

**Action:** Navigate to `http://localhost:3000/operations` (Operations & Reliability Console).

> *"In a high-stakes emergency service, reliability is life-or-death. Let us navigate to our **Operations & Reliability Console**.*
>
> *Here we monitor our runtime metrics, active telephony sessions, WebSocket gateway, and **Circuit Breakers**.*
>
> *SAMVED wraps every external provider — Sarvam STT, Sarvam TTS, Gemini LLM, Exotel Telephony, PostgreSQL, and Redis — in isolated circuit breakers. If Sarvam or Gemini suffers an upstream outage, our breakers trip into fast-fail mode, engaging local fallback models and deterministic templates in milliseconds without dropping the caller's call.*
>
> *We expose standard Kubernetes liveness (`/healthz`), readiness (`/ready`), and startup (`/health/startup`) probes, allowing seamless deployment on cloud Kubernetes clusters or air-gapped on-premise government servers."*

---

## Part 5: Conclusion & Question Alignment (4:30 – 5:00)

> *"To summarize:
> * **Linguistic Inclusion:** Seamless vernacular code-switching (Tamil/Hindi/Telugu/English).
> * **Mathematical Explainability:** Multimodal SVI scoring with factor-level attribution.
> * **Operator Empowerment:** 3-point warm transfer briefings reducing handoff time from minutes to seconds.
> * **Constitutional & Legal Grounding:** PWDVA 2005 & ERSS 112 integration with immutable SHA-256 audit trails.
> * **Engineering Rigor:** 629 automated tests passing with zero regressions across 16 implementation phases.
>
> *Thank you. We welcome your questions."*
