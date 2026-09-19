# SAMVED — Vercel Services Architecture & Deployment Guide

**System Version:** `v1.0.0-sih2026`  
**Classification:** Cloud Deployment Specification & Architectural Blueprint  

---

## 1. Overview & Architectural Comparison

SAMVED is designed to run in both local development/Docker environments and distributed cloud platforms such as **Vercel Services**.

```
+---------------------------------------------------------------------------------------------------+
|                                      VERCEL SERVICES ARCHITECTURE                                 |
|                                                                                                   |
|   +---------------------------------------+       +-------------------------------------------+   |
|   |         Next.js Web Service           |       |            FastAPI API Service            |   |
|   |             (apps/web)                |       |                (apps/api)                 |   |
|   |                                       |       |                                           |   |
|   |  - Operator Workstation Console       |       |  - HTTP Resolver (/v1/telephony/exotel/*) |   |
|   |  - Analytics & Triage Dashboard       |       |  - Realtime WS (/ws/telephony/exotel/*)   |   |
|   |  - Evaluation & Simulation Lab        |       |  - Operator WS (/ws/operator)             |   |
|   |  - Public Static & SSR Routes         |       |  - Deterministic Safety Engine            |   |
|   +---------------------------------------+       +-------------------------------------------+   |
|                       │                                                 │                         |
|                       │                                                 ▼                         |
|                       │                             +───────────────────────────────────────+     |
|                       │                             |       Managed Redis (e.g. Upstash)    |     |
|                       │                             |  - Session Envelopes (TTL 3600s)      |     |
|                       │                             |  - Provider Call ID Index             |     |
|                       │                             |  - Operator Pub/Sub Fanout Bus        |     |
|                       │                             |  - Distributed Sliding-Window Rate    |     |
|                       │                             +───────────────────────────────────────+     |
|                       │                                                 │                         |
|                       ▼                                                 ▼                         |
|   +───────────────────────────────────────────────────────────────────────────────────────────+   |
|   |                         Managed PostgreSQL (e.g. Supabase / Neon)                         |   |
|   |                           51 Relational Tables across 10 Subsystems                       |   |
|   +───────────────────────────────────────────────────────────────────────────────────────────+   |
+---------------------------------------------------------------------------------------------------+
```

### Architectural Comparison: Local vs. Vercel Production

| Dimension | Local Single-Process / Docker Compose | Vercel Services (Multi-Instance) |
|---|---|---|
| **Process Model** | Single Uvicorn worker per container. All HTTP routes and WebSockets share one memory space. | Dynamic auto-scaling container instances. Successive requests may hit different instances. |
| **Telephony Handshake** | HTTP GET resolver and subsequent WebSocket hit the **same** process. In-memory `active_sessions` dictionary suffices. | HTTP GET resolver hits **Instance A**; Exotel VoiceBot connects WebSocket to **Instance B**. In-memory lookup fails without Redis hydration. |
| **Operator Broadcast** | Direct local iteration over in-memory `operator_connections` list. | Operator browser may be connected to **Instance C**, while the call is processed on **Instance B**. Direct local broadcast fails to reach the operator without a distributed pub/sub bus. |
| **Rate Limiting** | In-memory sliding window dictionary. | Distributed sliding window in Redis via sorted sets (`ZADD`/`ZREMRANGEBYSCORE`/`ZCARD`) ensuring global quota enforcement. |
| **Persistence Layer** | Local container PostgreSQL + Redis (`init.sql` applied on container startup). | Managed cloud PostgreSQL (Neon/Supabase) + Managed Redis (Upstash/Aiven). |

---

## 2. The Multi-Instance Telephony Decoupling Problem

When Exotel handles an incoming PSTN call:
1. **Step 1 (HTTP Resolver):** Exotel sends a `GET /v1/telephony/exotel/inbound?CallSid=...` request to SAMVED to resolve the dynamic WebSocket stream URL.
2. **Step 2 (Session Creation):** SAMVED provisions a `TelephonySession` (e.g., `SESS-abc12345`), creates a call record, and returns:
   ```json
   {
     "url": "wss://samved-api.vercel.app/ws/telephony/exotel/SESS-abc12345"
   }
   ```
3. **Step 3 (WebSocket Ingress):** Exotel initiates a WebSocket handshake to `wss://samved-api.vercel.app/ws/telephony/exotel/SESS-abc12345`.

### Why In-Memory State Fails on Vercel
In a serverless or multi-instance architecture:
- Step 1 executes on **Instance A**. The session object is stored in `Instance A`'s memory.
- Step 3 connects to **Instance B** (due to load balancing or independent routing).
- Without Redis, `Instance B` looks up `SESS-abc12345` in its local `active_sessions` dictionary, finds nothing, and rejects the WebSocket with `4004 Session not found`.

### The Solution: Redis Session Envelope Bridge
SAMVED implements distributed session persistence in `apps/api/app/core/redis.py` and `apps/api/app/realtime/session_manager.py`:
1. **On Session Creation (Instance A):**
   - The session envelope (containing session ID, call ID, caller hash, language, state, provider call ID, and timestamps) is serialized to JSON and stored in Redis under `samved:session:{session_id}` with a 3600-second TTL.
   - An index key `samved:provider_call:{call_sid}` is mapped to the session ID.
2. **On WebSocket Connection (Instance B):**
   - If the session is present in local memory, it is used immediately.
   - If absent from local memory, `hydrate_session_from_redis(session_id)` loads the envelope from Redis, reconstructs the `TelephonySession` with its full context, and registers it in `Instance B`'s local registry before accepting the WebSocket.
3. **On Session Termination:**
   - The envelope is safely deleted from Redis, and the call record is persisted to the database.

---

## 3. Distributed Operator Console Fanout (Pub/Sub)

The SAMVED Operator Console (`apps/web/app/calls/page.tsx`) maintains a persistent WebSocket connection to `/ws/operator` to receive real-time call events:
- Inbound audio transcript turns (ASR)
- SVI vulnerability score updates
- Acoustic stress and emotion analysis
- Gemini adaptive suggestions
- Safety Engine policy violations and intervention alerts

### The Cross-Instance Fanout Problem
If Operator 1 is connected to **Instance C**, and Call 123 is actively streaming on **Instance B**, events generated on Instance B would never reach Operator 1 if events were only broadcast to locally connected WebSockets.

### The Solution: Redis Pub/Sub Bus
In `apps/api/app/realtime/connection_manager.py`:
1. When an event is broadcast via `broadcast_to_operators(event)`:
   - It is sent to all locally connected operator WebSockets on the current instance.
   - It is simultaneously published to the Redis channel `samved:events:operator` with a unique `_instance_id` tag.
   - The Redis publish operation has a strict **50ms timeout** to ensure it never blocks the real-time audio pipeline.
2. Every SAMVED API instance runs a background listener task (`_redis_listen_loop()`):
   - Subscribes to `samved:events:operator`.
   - When a message arrives from another instance (`msg._instance_id != current_instance_id`), it broadcasts the event to all locally connected operator WebSockets.
   - Events originating from the same instance are ignored to prevent duplicate delivery.
3. **Graceful Fallback:** If Redis is unavailable or in local development mode, the system immediately falls back to local-only broadcast with zero errors.

---

## 4. Distributed Sliding-Window Rate Limiting

To protect against DoS and carrier webhook flooding across scaled instances:
- Implemented in `apps/api/app/core/redis.py` and `apps/api/app/security/rate_limit.py`.
- Uses an atomic Redis sorted set pipeline:
  ```
  ZREMRANGEBYSCORE key 0 (now - window)
  ZCARD key
  ZADD key now unique_member
  EXPIRE key window
  ```
- If the count exceeds `max_requests`, the request is rejected with `429 Too Many Requests`.
- If Redis is disconnected, the rate limiter falls back to an in-memory sliding window cache with a 10-second failure cooldown to prevent connection lag.

---

## 5. Database Schema Architecture (51 Relational Tables)

SAMVED's database schema is defined in `infra/db/init.sql` and comprises **51 tables** across 10 functional subsystems:

1. **Identity, Access & Session Context (7 tables):** Users, roles, permissions, audit logs, active sessions, session credentials, device fingerprints.
2. **Telephony Ingress & Call Records (5 tables):** Inbound calls, provider call metadata, SIP headers, call legs, stream events.
3. **Speech & Acoustic Intelligence (6 tables):** STT transcripts, acoustic features, vocal biomarkers, stress indices, emotion timelines, turn segments.
4. **Social Vulnerability Index - SVI (5 tables):** SVI assessment records, demographic indicators, geographic vulnerability, composite scores, risk levels.
5. **Deterministic Safety Engine (5 tables):** Policy rules, safety violations, intervention triggers, hard stops, audit trails.
6. **Adaptive Conversation & LLM Reasoning (5 tables):** Gemini conversation contexts, prompt templates, tool calls, reasoning traces, token usage.
7. **Legal & Policy Knowledge RAG (4 tables):** Legal knowledge chunks, policy vectors, document embeddings, citation metadata.
8. **Case Intelligence & Knowledge Graph (5 tables):** Victims, entities, relationships, case graphs, evidence linkages.
9. **Follow-Up & Worker Task Workflow (5 tables):** Follow-up tasks, worker assignments, reminder schedules, status transitions, SLA trackers.
10. **District Intelligence & Evaluation (4 tables):** District incident rollups, geospatial aggregates, evaluation benchmark runs, metric logs.

> [!NOTE]
> In local development and mock mode, domain services operate using thread-safe in-memory collections for zero-dependency execution. When `DATABASE_URL` is configured in production, asyncpg connections persist domain entities directly into the relational tables.

---

## 6. Vercel Services Configuration (`vercel.json`)

The repository includes a root `vercel.json` configuring Vercel Services:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "web": {
      "path": "apps/web",
      "buildCommand": "pnpm build",
      "framework": "nextjs"
    },
    "api": {
      "path": "apps/api",
      "entrypoint": "app.main:app",
      "runtime": "python3.11"
    }
  },
  "rewrites": [
    { "source": "/v1/:path*", "destination": "/api/v1/:path*" },
    { "source": "/ws/:path*", "destination": "/api/ws/:path*" },
    { "source": "/health", "destination": "/api/health" },
    { "source": "/ready", "destination": "/api/ready" },
    { "source": "/docs", "destination": "/api/docs" },
    { "source": "/openapi.json", "destination": "/api/openapi.json" },
    { "source": "/((?!api/|_next/|favicon.ico).*)", "destination": "/web/$1" }
  ]
}
```

### Environment Variable Matrix for Vercel

Configure the following environment variables in the Vercel Project Settings:

| Service | Variable Name | Required | Example / Purpose |
|---|---|---|---|
| **api** | `APP_ENV` | Yes | `production` |
| **api** | `APP_MODE` | Yes | `LIVE` |
| **api** | `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@ep-xyz.neon.tech/samved_prod` |
| **api** | `REDIS_URL` | Yes | `rediss://default:token@xyz.upstash.io:6379` |
| **api** | `EXOTEL_ACCOUNT_SID` | Yes | Exotel Account SID |
| **api** | `EXOTEL_API_KEY` | Yes | Exotel API Key |
| **api** | `EXOTEL_API_TOKEN` | Yes | Exotel API Token |
| **api** | `EXOTEL_CALLER_ID` | Yes | `04447615453` |
| **api** | `SARVAM_API_KEY` | Yes | Sarvam Indic STT/TTS Key |
| **api** | `GEMINI_API_KEY` | Yes | Google Gemini Generative AI Key |
| **api** | `PUBLIC_BASE_URL` | Yes | `https://samved.vercel.app` |
| **api** | `PUBLIC_WS_BASE_URL` | Yes | `wss://samved.vercel.app` |
| **api** | `EXOTEL_WEBHOOK_BASE_URL` | Yes | `https://samved.vercel.app/v1/telephony` |
| **api** | `EXOTEL_STREAM_URL` | Yes | `wss://samved.vercel.app/ws/telephony/exotel` |
| **api** | `JWT_SECRET` | Yes | High-entropy 64-character secret |
| **web** | `NEXT_PUBLIC_API_URL` | Yes | `https://samved.vercel.app` |
| **web** | `NEXT_PUBLIC_WS_URL` | Yes | `wss://samved.vercel.app/ws` |
| **web** | `NEXT_PUBLIC_APP_MODE` | Yes | `LIVE` |

---

## 7. Verification Checklist

Before directing live PSTN telephony traffic to Vercel:
- [x] All 458 backend tests passing (`test_vercel_readiness.py` covering envelope save/hydrate, operator pub/sub, sliding-window rate limit).
- [x] Frontend type-checking passed (`pnpm type-check`).
- [x] Frontend production build compiled cleanly (`pnpm build`).
- [x] Playwright smoke tests passed (`pnpm test:e2e smoke.spec.ts`).
- [x] Docker Compose configuration validated (`docker compose config`).
- [x] `/ready` endpoint reports Redis and database status.
- [x] Connection failure cooldowns ensure zero-latency fallback when Redis is offline in local dev.
