# SAMVED — System Architecture & Data Flow Topology

**Smart India Hackathon 2026 | PS-26093**  
**System Version:** `v1.0.0-sih2026`  
**Classification:** Enterprise Micro-Service System for Emergency Helpline Triage

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Ingestion["Ingestion Layer"]
        Caller["Distressed Caller (PSTN / Mobile)"] --> Exotel["Exotel / Telephony Gateway (8kHz PCM)"]
        Exotel --> FastAPIGateway["FastAPI Gateway (Uvicorn / ASGI)"]
    end

    subgraph Intelligence["Real-Time AI Intelligence Layer"]
        FastAPIGateway --> CircuitSTT["Circuit Breaker: Sarvam Indic ASR"]
        CircuitSTT --> STT["Code-Switching ASR (ta, hi, te, en)"]
        
        FastAPIGateway --> Acoustic["Acoustic Distress Engine (f0 Tremor, Pitch Variance)"]
        
        STT & Acoustic --> SafetyEngine["Safety Screening & Intent Classifier"]
        SafetyEngine --> SVIEngine["Statistical Vulnerability Index (SVI 0-100)"]
        
        SVIEngine --> AdaptiveEngine["Adaptive Dialogue & Protocol Selector (P0-P3)"]
        
        AdaptiveEngine --> CircuitLLM["Circuit Breaker: Gemini 2.5 LLM"]
        CircuitLLM --> KnowledgeRAG["Indian Statutory RAG (PWDVA, ERSS 112, IRCA)"]
        
        KnowledgeRAG --> CaseGraph["Case Intelligence Graph (Entities, Relations)"]
    end

    subgraph Governance["Governance & Security Layer"]
        PIIScrubber["Indian PII Redaction Pipeline (Aadhaar, PAN, Phone)"]
        MerkleChain["SHA-256 Tamper-Evident Merkle Audit Log"]
        RBAC["5-Tier Role-Based Access Control (IDOR Protected)"]
        
        Intelligence --> PIIScrubber --> MerkleChain
        RBAC -.-> FastAPIGateway
    end

    subgraph Presentation["Operator & Supervisor Workstations"]
        FastAPIGateway <--> WSManager["WebSocket Broadcast Gateway (/ws/v1/operator)"]
        WSManager <--> OperatorConsole["Operator Workstation & Tele-Counselor Briefing"]
        WSManager <--> DemoHub["SIH 2026 Demo Hub (/demo)"]
        WSManager <--> OpsConsole["Operations & Reliability Console (/operations)"]
    end

    subgraph Storage["Persistence Layer"]
        Postgres[(PostgreSQL 16: Cases, Records, Graphs)]
        Redis[(Redis 7: Ephemeral Sessions & Audio Buffers)]
        FastAPIGateway <--> Postgres & Redis
    end
```

---

## 2. 8-Stage Real-Time Pipeline Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Caller
    participant Telephony as Telephony Subsystem
    participant STT as Sarvam Indic ASR
    participant Safety as Deterministic Safety Engine
    participant SVI as SVI Assessment Engine
    participant Adaptive as Adaptive Protocol Engine
    participant Copilot as Warm Transfer Copilot
    participant RAG as Statutory Knowledge RAG
    participant Graph as Case Intelligence Graph
    participant Audit as Cryptographic Audit Chain
    actor Operator as Human Tele-Counselor

    Caller->>Telephony: Speaks mixed Tamil/English duress utterance
    Telephony->>STT: Stream 8kHz audio frame
    STT->>Safety: Transcribed turn + Acoustic stress (0.94)
    Safety->>SVI: Flags IMMINENT_VIOLENCE, WEAPON_INVOLVED, INFANT_PRESENT
    SVI->>Adaptive: Computes SVI 88/100 (CRITICAL Band)
    Adaptive->>Copilot: Triggers Protocol P0 (Emergency Dispatch Assist)
    Copilot->>RAG: Synthesizes 3-point briefing; queries statutory protections
    RAG->>Graph: Injects PWDVA 2005 Sec 12 & ERSS 112 SOPs
    Graph->>Audit: Updates Case CASE-2026-SIH-001 entity relations
    Audit->>Operator: Computes SHA-256 Merkle hash; pushes live card via WebSocket
    Note over Operator: Operator inspects 3-point brief & verifies 112 dispatch
```

---

## 3. Circuit Breaker Fault Isolation Topology

```mermaid
stateDiagram-v2
    [*] --> CLOSED: System Startup

    CLOSED --> OPEN: Failure Count >= Threshold (e.g. 5 consecutive timeouts)
    note right of CLOSED
        Nominal operation:
        Requests pass to external API
    end note

    OPEN --> HALF_OPEN: Recovery Timeout Expired (e.g. 30s)
    note right of OPEN
        Fast-Fail active:
        Calls immediately routed to local fallback
        Zero upstream latency delay
    end note

    HALF_OPEN --> CLOSED: Trial Request Succeeds
    HALF_OPEN --> OPEN: Trial Request Fails

    OPEN --> CLOSED: Manual Operator Reset via /operations Console
```

---

## 4. Cryptographic Non-Repudiation Audit Chain

Every critical event is chained to ensure absolute evidentiary provenance:

$$\text{Block Hash}_n = \text{SHA-256}\Big(\text{Hash}_{n-1} \parallel \text{Timestamp} \parallel \text{Actor} \parallel \text{Action} \parallel \text{Resource} \parallel \text{Sanitized Payload}\Big)$$

If any historical record is altered in the PostgreSQL database, verifying the chain via `GET /v1/security/audit/verify` detects a hash mismatch at the modified block, guaranteeing non-repudiation for statutory authorities and courts.
