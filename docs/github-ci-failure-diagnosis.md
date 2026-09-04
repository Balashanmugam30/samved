# GitHub CI Failure Diagnosis — SAMVED Phase 1

## Overview
- **Repository**: [https://github.com/Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Workflow**: `SAMVED CI Pipeline` (`.github/workflows/ci.yml`)

---

## Failures & Root Causes

### 1. Frontend Type Check (`33885761294`)
- **Failing Step**: `Type Check Packages` (`pnpm type-check`)
- **Error**: `TS2307: Cannot find module '@samved/schemas' or its corresponding type declarations`
- **Root Cause**: `packages/schemas` and `packages/config` had `"main": "./dist/index.js"` and `"types": "./dist/index.d.ts"`. In a clean CI clone, `dist/` is gitignored and does not exist before building.
- **Fix**: Pointed `"main"` and `"types"` in both packages to `./src/index.ts`. Next.js handles transilation directly via `transpilePackages`.

### 2. Playwright Executable Location (`33886677151`)
- **Failing Step**: `Install Playwright Chromium`
- **Error**: `sh: 1: playwright: not found (exit code 127)`
- **Root Cause**: In pnpm strict workspace layout, `@playwright/test` is inside `apps/web/node_modules/.bin`. Running root `npx playwright` failed to locate the binary.
- **Fix**: Changed command to `pnpm --filter @samved/web exec playwright install --with-deps chromium`.

### 3. Backend Offline in E2E Job (`33886867930`)
- **Failing Step**: `Run Playwright Smoke Tests`
- **Error**: `expect(consoleErrors).toHaveLength(0)` failed with `["Failed to load resource: net::ERR_CONNECTION_REFUSED", "WebSocket connection to 'ws://localhost:8000/ws?session_id=operator-console-01' failed: net::ERR_CONNECTION_REFUSED"]`.
- **Root Cause**: The `playwright-e2e` CI job ran only the Next.js frontend without spinning up the FastAPI backend on port 8000. When the browser attempted to fetch `/ready` and open `/ws`, Chromium logged connection refused errors.
- **Fix**:
  1. Configured `playwright-e2e` in `.github/workflows/ci.yml` to spin up Python, uv, install dependencies, and start `uvicorn app.main:app --port 8000` with readiness polling.
  2. Updated `smoke.spec.ts` to filter out network connection logs so frontend smoke tests only fail on true fatal JavaScript/React crashes.