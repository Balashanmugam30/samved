# SAMVED — Failure Modes & Graceful Degradation Runbook

**System Version:** `v1.0.0-sih2026`  
**Classification:** Operational Reliability & Business Continuity Runbook

---

## 1. Failure Mode Matrix

| Failure Mode | Detection Trigger | Circuit Breaker Action | Degradation Pathway | Operator Impact | Recovery Action |
|---|---|---|---|---|---|
| **Sarvam Indic STT Outage** | 5 consecutive HTTP 5xx / timeouts (>3000ms) | `sarvam-stt` trips to `OPEN` | Fast-fails to local Conformer/Whisper mock pipeline; preserves active audio session. | Banner appears: "STT operating in local fallback mode". | Automatic after 30s cooldown; or manual reset via `/operations` console. |
| **Gemini LLM Quota / Timeout** | 5 consecutive API errors / rate limits (429) | `gemini-llm` trips to `OPEN` | Bypasses generative LLM; engages deterministic regex safety screening & static statutory guidance. | AI suggestions locked to vetted safety templates. | Check API quota; switch API key in `.env`; reset breaker via `/operations`. |
| **Exotel Webhook Failure** | Signature verification failure or gateway drop | `exotel-telephony` breaker alerts | Drops unverified payload; falls back to telephony simulation harness for development/eval. | Unauthorized calls rejected (HTTP 403); active calls continue. | Verify `EXOTEL_WEBHOOK_SECRET` in environment variables. |
| **PostgreSQL Outage** | Connection pool exhausted / timeout | `database` trips to `OPEN` | Shifts writes into in-memory ephemeral buffer with circular eviction; persists in Redis. | Workstation shows: "Database write degraded — logging to ephemeral memory". | Restart PostgreSQL container; execute backup restore if disk corrupted. |
| **Redis Crash** | Redis ping fails 3 consecutive times | `redis` trips to `OPEN` | Telephony sessions fall back to local in-memory Python dictionaries with thread locks. | WebSocket pub/sub restricted to single node. | `docker compose restart redis`; inspect `/var/log/redis/redis-server.log`. |
| **Operator WebSocket Disconnect** | Heartbeat timeout / ping drop | Reconnect loop initiated | Client queues unacknowledged user interactions locally; auto-reconnects with exponential backoff. | Small reconnection spinner; updates auto-sync upon reconnection. | Verify reverse proxy (Nginx) WebSocket timeout (`proxy_read_timeout 3600s`). |

---

## 2. Step-by-Step Operator & Administrator Runbooks

### Runbook A: External Provider Spike / Circuit Breaker Reset
1. Navigate to the **Operations & Reliability Console** (`http://localhost:3000/operations`).
2. Identify the tripped circuit breaker (highlighted in red `OPEN` status, e.g. `sarvam-stt` or `gemini-llm`).
3. Verify upstream provider status on their respective public status dashboards.
4. If upstream has recovered, click **Reset** on the individual circuit card or click **Reset All Circuit Breakers**.
5. Observe that state transitions to `CLOSED` and throughput normalizes.

### Runbook B: Complete Network Air-Gap / Offline Evaluation Mode
1. In disconnected or hackathon judging environments where public Internet is firewalled:
2. Ensure `.env` has `APP_MODE=DEV` or `APP_MODE=SIMULATION`.
3. In this mode, SAMVED automatically substitutes external APIs with high-fidelity, deterministic synthetic models.
4. Confirm system status at `http://localhost:8000/ready` (returns `200 READY`).
5. Conduct evaluations seamlessly on the **SIH Demo Hub** (`/demo`).
