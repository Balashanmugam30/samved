# SAMVED — Realtime Event Envelope & Taxonomy Specification (v1.0)

## 1. Canonical Event Envelope
All real-time communications over the SAMVED WebSocket Gateway (`/ws`) and internal streaming message buses conform to the `EventEnvelope` schema.

```json
{
  "event_id": "8f88c83a-8693-41bb-98f5-961d76ea6ee5",
  "event_type": "SVI_UPDATED",
  "schema_version": "1.0",
  "timestamp": "2026-09-04T13:45:00.123Z",
  "session_id": "sess-92f7c001",
  "call_id": "call-e3204910",
  "case_id": "case-2026-0901",
  "payload": {
    "score": 68,
    "band": "HIGH",
    "confidence": 0.94,
    "contributing_factors": [
      {
        "factor": "acute_withdrawal",
        "weight": 0.45,
        "evidence": "physical shivering reported"
      },
      {
        "factor": "severe_isolation",
        "weight": 0.35,
        "evidence": "no family contact"
      }
    ],
    "is_clinical_diagnosis": false
  }
}
```

### Key Envelope Fields
- `event_id`: Unique UUIDv4 identifying this discrete event.
- `event_type`: Strongly typed enumeration value from `EventType`.
- `schema_version`: Semantic schema version (current: `"1.0"`). All breaking changes increment the major version.
- `timestamp`: ISO-8601 UTC timestamp generated at source. Frontend timestamps are never trusted as backend ground truth.
- `session_id`: Unique correlation token for the active WebSocket / telemetry session.
- `call_id`: Telephone call identifier assigned during telephony ingress.
- `case_id`: Optional associated victim case identifier (null during initial anonymous intake).
- `payload`: Strongly typed object defined per `event_type`.

---

## 2. Complete Event Taxonomy (20 Core Events)

| Category | Event Type | Description |
| :--- | :--- | :--- |
| **Telephony Lifecycle** | `CALL_STARTED` | Telecom ingress detected call initiation from helpline number 14566. |
| | `CALL_CONNECTED` | Audio stream bi-directionally established with telephony provider. |
| | `CALL_ENDED` | Call ended; includes duration and hangup/transfer reason. |
| **Speech & Language** | `LANGUAGE_DETECTED` | ASR engine identified caller language (e.g. Hindi, Tamil, Bengali). |
| | `LANGUAGE_CHANGED` | Dynamic code-switching or language shift identified mid-dialogue. |
| | `TRANSCRIPT_PARTIAL` | Low-latency interim speech-to-text hypothesis from Sarvam STT. |
| | `TRANSCRIPT_FINAL` | Confirmed final utterance transcript with confidence and timing. |
| | `ACOUSTIC_UPDATE` | Paralinguistic features (pitch variation, jitter, shimmer, pause ratio). |
| **Safety & Vulnerability** | `SAFETY_SIGNAL` | Deterministic safety rule triggered (physical danger, self-harm). |
| | `RISK_UPDATED` | Immediate threat or vulnerability indicator calculated. |
| | `SVI_UPDATED` | Stress Vulnerability Index updated (Score 0–100 and Low/Mod/High/Crit band). |
| **Agent & AI Action** | `AGENT_ACTION` | Specialized agent action executed (e.g. legal lookup, case draft). |
| | `AI_RESPONSE_STARTED` | Generation / synthesis of spoken response initiated. |
| | `AI_RESPONSE_ENDED` | Audio transmission of response completed to telephony leg. |
| **Escalation & Oversight** | `HUMAN_ALERT` | Priority alert dispatched to operator console. |
| | `ESCALATION_RECOMMENDED` | Automated recommendation for tele-counselor or supervisor takeover. |
| | `ESCALATION_ACCEPTED` | Human operator accepted escalation and took control. |
| | `ESCALATION_OVERRIDDEN` | Human operator dismissed or altered automated recommendation. |
| **Case & Followup** | `CASE_CREATED` | New victim case record created with consent. |
| | `FOLLOWUP_SCHEDULED` | Outbound check-in or counseling appointment scheduled. |

---

## 3. Heartbeat & Keepalive Protocol
To prevent silent TCP connection drops through stateful firewalls:
- Clients or servers emit `HEARTBEAT_PING`.
- Receiver immediately replies with `HEARTBEAT_PONG` containing `{"reply_to": "<event_id>"}`.
- Failure to receive pong within 60s triggers clean reconnection with exponential backoff.
