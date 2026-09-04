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
- **Fix**: Pointed `"main"` and `"types"` in both packages to `./src/index.ts`. Next.js handles transpilation directly via `transpilePackages`.

### 2. Playwright Executable Location (`33886677151`)
- **Failing Step**: `Install Playwright Chromium`
- **Error**: `sh: 1: playwright: not found (exit code 127)`
- **Root Cause**: In pnpm strict workspace layout, `@playwright/test` is inside `apps/web/node_modules/.bin`. Running root `npx playwright` failed to locate the binary.
- **Fix**: Changed command to `pnpm --filter @samved/web exec playwright install --with-deps chromium`.

### 3. Backend Offline in E2E Job & Strict Locator Match (`33886867930` & `33887280917`)
- **Failing Step**: `Run Playwright Smoke Tests`
- **Errors**:
  1. Offline backend resulted in browser network errors (`ERR_CONNECTION_REFUSED`).
  2. Once backend connected live, welcome message JSON payload on the dashboard displayed `Realtime Gateway`, causing Playwright's `locator('text=Realtime Gateway')` to match two DOM elements (card title and JSON body).
- **Fix**:
  1. Configured `playwright-e2e` in `.github/workflows/ci.yml` to start `uvicorn app.main:app --port 8000` with readiness polling.
  2. Updated `smoke.spec.ts` to use exact text matching `getByText('Realtime Gateway', { exact: true })` and filter transient network connection logs.