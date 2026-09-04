# SAMVED — Developer Environment & Setup Guide

## 1. Prerequisites
- **Node.js**: v20.x or v22.x (`node --version`)
- **pnpm**: v9.x or v10.x (`pnpm --version`)
- **Python**: v3.11+ (Python 3.13 tested) with `uv` (`uv --version`)
- **Git**: v2.40+
- **Optional**: Docker & Docker Compose for containerized PostgreSQL and Redis

---

## 2. Quickstart Step-by-Step

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/Balashanmugam30/samved.git
cd samved

# Copy environment template
cp .env.example .env
```

### Step 2: Install Frontend & Shared Node Packages
```bash
pnpm install
```

### Step 3: Setup Python Environment for API
```bash
cd apps/api
# Using uv (recommended):
uv venv
uv pip install -r requirements.txt

# Or using standard venv:
# python -m venv .venv
# .venv\Scripts\activate   # Windows
# source .venv/bin/activate # macOS/Linux
# pip install -r requirements.txt
```

---

## 3. Running Services Locally

### Running the FastAPI Backend
```bash
# From apps/api:
uv run uvicorn app.main:app --reload --port 8000

# Or from repository root:
pnpm dev:api
```
- API Base: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Liveness Check: `http://localhost:8000/health`
- Readiness Check: `http://localhost:8000/ready`
- Version Info: `http://localhost:8000/version`
- WebSocket Gateway: `ws://localhost:8000/ws`

### Running the Next.js Web Console
```bash
# From repository root:
pnpm --filter @samved/web dev
```
- Web Console: `http://localhost:3000`

---

## 4. Running Automated Tests

### Backend Unit, Contract & WebSocket Tests
```bash
# Run pytest from apps/api:
cd apps/api
uv run pytest -v

# Run with test coverage:
uv run pytest --cov=app tests/
```

### Frontend Type Checking & Production Build
```bash
# Run TypeScript compilation checks:
pnpm type-check

# Run Next.js production build:
pnpm build
```

### Playwright E2E Smoke Tests
```bash
# Run Playwright tests from apps/web:
cd apps/web
pnpm test:e2e

# Run with interactive UI mode:
pnpm exec playwright test --ui
```

---

## 5. Docker Local Infrastructure (Optional)
To run local PostgreSQL and Redis containers:
```bash
docker compose up -d postgres redis
```
To run the full containerized stack:
```bash
docker compose up --build
```
