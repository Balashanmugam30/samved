# GitHub CI Failure Diagnosis — SAMVED Phase 1

## Overview
- **Repository**: [https://github.com/Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Commit**: `bda59a1` & `7472559`
- **Workflow**: `SAMVED CI Pipeline` (`.github/workflows/ci.yml`)
- **Initial Run ID**: `33885761294` (Failing Job: `Frontend Type Check & Build`)
- **Second Run ID**: `33886677151` (Failing Job: `Playwright Browser Smoke Tests`)

---

## Diagnostic Breakdown

### FAILURE 1: Frontend Type Check
`pnpm type-check` in `frontend-checks` failed with exit code 2 and TypeScript compiler errors:
```text
apps/web type-check: src/app/page.tsx(7,27): error TS2307: Cannot find module '@samved/schemas' or its corresponding type declarations.
apps/web type-check: src/hooks/useWebSocket.ts(4,42): error TS2307: Cannot find module '@samved/schemas' or its corresponding type declarations.
```

**Root Cause**: In `packages/schemas/package.json` and `packages/config/package.json`, entry points were configured to `./dist/index.d.ts`. Since `dist/` is gitignored and `pnpm type-check` ran before `pnpm build`, declarations were missing.
**Fix**: Updated `packages/schemas/package.json` and `packages/config/package.json` to point `"main"` and `"types"` directly to `./src/index.ts` (leveraging `transpilePackages`).

### FAILURE 2: Playwright Executable Discovery
`npx playwright install --with-deps chromium` failed in CI with:
```text
sh: 1: playwright: not found
Process completed with exit code 127.
```

**Root Cause**: In a strict pnpm workspace, `@playwright/test` is installed under `apps/web/node_modules/.bin`, not the monorepo root. `npx` run from the root fails to locate the binary.
**Fix**: Changed step to `pnpm --filter @samved/web exec playwright install --with-deps chromium` and added `pnpm build` before smoke tests.

### AFFECTED FILES:
1. `packages/schemas/package.json`
2. `packages/config/package.json`
3. `.github/workflows/ci.yml`
4. `package.json`
5. `docs/github-ci-failure-diagnosis.md`