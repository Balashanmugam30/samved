# SAMVED Localhost Development Runbook

This runbook provides verified, step-by-step instructions for setting up, running, testing, and verifying SAMVED on a local development workstation (Windows PowerShell and Linux/macOS).

---

## 1. Prerequisites & Environment

| Component | Minimum Version | Verified Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Node.js** | `>= 20.0.0` | `v20.x` / `v22.x` | Next.js Frontend & TypeScript monorepo |
| **pnpm** | `>= 9.0.0` | `v9.x` | Fast workspace package manager |
| **Python** | `>= 3.11` | `3.13.6` | FastAPI Realtime Backend |
| **uv** | `>= 0.4.0` | `v0.4.x+` | Ultra-fast Python package & environment manager |
| **Git** | `>= 2.40` | Latest | Source control |

---

## 2. Port Allocations

SAMVED allocates distinct ports to prevent local conflicts:

| Port | Service | Protocol | Default Bind |
| :--- | :--- | :--- | :--- |
| **3000** | Next.js Operator Web Console | HTTP / HTML | `http://localhost:3000` |
| **8000** | FastAPI Telephony & AI Backend | HTTP / REST & WS | `http://localhost:8000` |
| **5432** | PostgreSQL Database (Phase 4+) | TCP | `localhost:5432` |
| **6379** | Redis Pub/Sub & State (Phase 4+) | TCP | `localhost:6379` |

---

## 3. Initial Setup

### Clone and Install Dependencies

```powershell
# In PowerShell (Windows) or Bash (Linux/macOS)
git clone https://github.com/Balashanmugam30/samved.git
cd samved

# Install all JavaScript/TypeScript monorepo dependencies
pnpm install

# Build shared schema contracts
pnpm --filter @samved/schemas build
pnpm --filter @samved/config build

# Initialize Python virtual environment with uv
uv --directory apps/api sync
```

### Environment Configuration

Copy the example environment configuration:
```powershell
# Backend environment
cp apps/api/.env.example apps/api/.env

# Frontend environment
cp apps/web/.env.example apps/web/.env.local
```

Default developer values run in `APP_MODE=DEV` (or `SIMULATION`), requiring zero third-party credentials or paid telecom credits.

---

## 4. Running the Development Stack

### Terminal 1: FastAPI Realtime Backend
```powershell
uv --directory apps/api run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Health Check: `http://localhost:8000/health`
- OpenAPI Docs: `http://localhost:8000/docs`
- Dedicated Operator WebSocket: `ws://localhost:8000/ws/operator`
- Telephony Audio Ingress: `ws://localhost:8000/ws/telephony/exotel`

### Terminal 2: Next.js Operator Console
```powershell
pnpm --filter @samved/web dev
```
- Web Application: `http://localhost:3000`
- Operator Console: `http://localhost:3000/calls`

---

## 5. Verification Commands

### Run Backend Unit & WebSocket Test Suite
```powershell
uv --directory apps/api run pytest -v
```
*Expected: 52+ tests passing.*

### Run Monorepo Type Check
```powershell
pnpm type-check
```

### Run Production Build
```powershell
pnpm build
```

### Run Playwright E2E Tests
```powershell
pnpm test:e2e
```
*Expected: 12 passing tests across Desktop Chrome and Mobile Chrome.*

---

## 6. Running a Voice Simulation

You can trigger conversational simulations either via the UI or directly via `curl` / PowerShell:

```powershell
# Trigger Tamil Distress & Safety Verification simulation
Invoke-RestMethod -Uri "http://localhost:8000/v1/telephony/simulate/conversation" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"scenario_key": "tamil_help", "caller_number": "+919876543210"}'
```

View the live conversation turns, partial drafts, and latency metrics in real-time at `http://localhost:3000/calls`.
