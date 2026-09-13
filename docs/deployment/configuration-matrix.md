# SAMVED — Deployment Configuration Matrix

**System Version:** `v1.0.0-sih2026`  
**Classification:** Environment Configuration Specification

---

## 1. Environment Profiles Overview

SAMVED supports 4 primary deployment modes governed by `APP_ENV` and `APP_MODE`:

| Profile | `APP_ENV` | `APP_MODE` | Target Environment | Primary Purpose |
|---|---|---|---|---|
| **Development** | `development` | `DEV` | Local Workstation | Feature development, local debugging, mock telephony. |
| **CI / Automated Test** | `test` | `DEV` / `SIMULATION` | GitHub Actions Runner | Deterministic unit, contract, and Playwright browser smoke tests. |
| **SIH 2026 Demo** | `staging` / `development` | `DEV` (`DEMO_MODE=True`) | Evaluation / Judging Lab | Fast, deterministic evaluation of all 8 pipeline stages with flagship Tamil/English crisis scenario. |
| **Production-Like Live** | `production` | `LIVE` | Cloud VPS / Government DC | Real PSTN calls via Exotel webhook, live Sarvam STT/TTS, and Gemini LLM. |

---

## 2. Configuration Parameters by Profile

| Parameter | Development (DEV) | SIH Demo (DEMO) | Production-Like (LIVE) | Description |
|---|---|---|---|---|
| `LOG_LEVEL` | `DEBUG` | `INFO` | `INFO` / `WARNING` | Console verbosity level |
| `STRUCTURED_LOGGING` | `false` | `true` | `true` | JSON structured log format |
| `DEMO_MODE_ENABLED` | `true` | `true` | `false` | Enables `/v1/demo/` endpoints & reset actions |
| `CIRCUIT_FAILURE_THRESHOLD` | `5` | `5` | `5` | Failures before circuit trips OPEN |
| `CIRCUIT_RECOVERY_TIMEOUT` | `10.0` | `15.0` | `30.0` | Seconds before testing recovery |
| `EXOTEL_ACCOUNT_SID` | Optional (Mock) | Optional (Mock) | **Required** | Exotel Telephony Account SID |
| `EXOTEL_API_KEY` | Optional (Mock) | Optional (Mock) | **Required** | Exotel API Key |
| `EXOTEL_VERIFY_SIGNATURE` | `false` | `false` | `true` | Cryptographic HMAC signature check |
| `SARVAM_API_KEY` | Optional (Mock) | Optional (Mock) | **Required** | Sarvam Indic ASR/TTS API Key |
| `GEMINI_API_KEY` | Optional (Mock) | Optional (Mock) | **Required** | Google Gemini Generative AI Key |
| `DATABASE_URL` | Optional / Local | Optional / Local | **Required** | PostgreSQL asyncpg connection string |
| `REDIS_URL` | Optional / Local | Optional / Local | **Required** | Redis URL for session/audio caching |

---

## 3. Environment Protection Invariants

> [!CAUTION]
> **Production Safety Invariant:**
> When `APP_MODE == "LIVE"` or `APP_ENV == "production"`:
> 1. All `/v1/demo/reset` requests return `403 FORBIDDEN`.
> 2. Synthetic database overwrites are completely disabled.
> 3. Strict signature verification is enforced on all incoming telephony webhooks when configured.
> 4. Health checks (`/ready`) will report `503 NOT_READY` if live database or live telephony credentials are missing.

---

## 4. Host Network Addressing: Local Windows vs. Docker Compose

To ensure seamless execution whether running directly on the developer host or containerized via Docker Compose, network service addressing is governed by execution context:

| Context | `DATABASE_URL` Host | `REDIS_URL` Host | Resolution Mechanism |
|---|---|---|---|
| **Direct Windows API** | `localhost:5432` | `localhost:6379` | Read directly from `apps/api/.env` where containers expose ports `5432:5432` and `6379:6379`. |
| **Docker Compose API** | `postgres:5432` | `redis:6379` | Overridden in `docker-compose.yml` under `services.api.environment` to resolve Docker container service names over the internal bridge network. |

### Configuration Precedence in Docker Compose
Docker Compose loads `apps/api/.env` via `env_file:`:
- All provider keys (`SARVAM_API_KEY`, `GEMINI_API_KEY`, `EXOTEL_*`), `APP_MODE`, and security parameters are ingested from `apps/api/.env`.
- `DATABASE_URL` and `REDIS_URL` are explicitly set under `services.api.environment`, taking precedence over the localhost URLs in `apps/api/.env` and directing traffic to the internal container bridge.

---

## 5. Live Mode Deployment Requirements

When transitioning to `APP_MODE=LIVE`:
1. **Real Provider Credentials Required**:
   - `EXOTEL_ACCOUNT_SID`, `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`
   - `SARVAM_API_KEY` (minimum 8 characters)
   - `GEMINI_API_KEY` (minimum 8 characters)
2. **Public Ingress Endpoint Required**:
   - Telephony carriers (Exotel) cannot reach private `localhost` addresses.
   - `PUBLIC_BASE_URL` (HTTPS) and `PUBLIC_WS_BASE_URL` (WSS) must resolve to a valid public hostname (e.g. Cloudflare Tunnel, ngrok, or cloud reverse proxy).
   - `EXOTEL_WEBHOOK_BASE_URL` and `EXOTEL_STREAM_URL` point to the respective webhook routes on this public host.
3. **Exotel App Bazaar Flow**:
   - Passthru applet configured for `POST /v1/telephony/exotel/inbound`.
   - Voicebot / Stream applet configured for bidirectional 16-bit 8kHz PCM streaming to `wss://<DOMAIN>/ws/telephony/exotel/{CustomField}`.

---

## 6. Secret Configuration & Governance Notice

> [!IMPORTANT]
> **Strict Secret Isolation:**
> `apps/api/.env` contains local, confidential runtime secrets and credentials. It is strictly excluded from version control via `.gitignore` and `.dockerignore`.
> - **NEVER** commit `apps/api/.env` or any `.env*` variant containing plaintext keys to Git.
> - **NEVER** bake credentials into Dockerfiles or client-facing bundles.
> - The Next.js web application is completely isolated from backend provider secrets. Only non-sensitive variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.
