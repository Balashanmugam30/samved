# Contributing to SAMVED

Thank you for contributing to SAMVED (Smart India Hackathon 2026 — Problem Statement 26093).

## 1. Development Principles
- **No fake telemetry**: Do not manufacture fake AI metrics or placeholder telemetry that misleads operators or reviewers.
- **Provider neutrality**: Maintain clean interfaces for Telephony (`TelephonyProvider`), STT (`SpeechToTextProvider`), TTS (`TextToSpeechProvider`), and LLMs (`LLMProvider`).
- **Deterministic safety priority**: Never delegate core victim safety decisions solely to probabilistic LLM outputs.
- **Strict secret hygiene**: Always verify `.gitignore` before staging commits. Never commit `.env` files.

## 2. Monorepo Setup
SAMVED is structured as a monorepo:
- `apps/web`: Next.js 14/15, TypeScript, Tailwind CSS
- `apps/api`: FastAPI, Pydantic v2, WebSockets, Python 3.13
- `packages/schemas`: Shared domain and event contracts
- `packages/config`: Shared configuration constants
- `services/`: Specialized service boundaries
- `docs/`: In-depth architectural, event, and security documentation

### Prerequisites
- Node.js 20+ & pnpm 9+
- Python 3.11+ (Python 3.13 recommended) with `uv` or `pip`
- Optional: Docker & Docker Compose for PostgreSQL/Redis

### Local Installation
```bash
# 1. Clone the repository
git clone https://github.com/Balashanmugam30/samved.git
cd samved

# 2. Configure environment
cp .env.example .env

# 3. Install frontend & shared TypeScript packages
pnpm install

# 4. Set up Python API environment
cd apps/api
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Quality Standards
Before opening a PR, ensure all checks pass:
```bash
# Frontend type check & build
pnpm --filter web type-check
pnpm --filter web build

# Backend tests
pytest apps/api/tests -v

# E2E Playwright smoke tests
pnpm --filter web test:e2e
```

## 4. Branching & Commits
- Use descriptive branch names: `feature/brief-description`, `fix/issue-description`, `docs/summary`.
- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
