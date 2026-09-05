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
> 3. Strict signature verification is enforced on all incoming telephony webhooks.
> 4. Health checks (`/ready`) will report `503 NOT_READY` if live database or live telephony credentials are missing.
