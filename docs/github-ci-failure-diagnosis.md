# GitHub CI Failure Diagnosis — SAMVED Phase 1

## Overview
- **Repository**: [https://github.com/Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Commit**: `bda59a1` (`feat: implement Exotel realtime telephony gateway (Phase 1)`)
- **Workflow**: `SAMVED CI Pipeline` (`.github/workflows/ci.yml`)
- **Run ID**: `33885761294`
- **Failing Job**: `Frontend Type Check & Build` (Job ID `101065002281`)
- **Failing Step**: `Type Check Packages` (`pnpm type-check`)

---

## Diagnostic Breakdown

### FAILURE:
`pnpm type-check` in `frontend-checks` failed with exit code 2 and TypeScript compiler errors:
```text
apps/web type-check: src/app/page.tsx(7,27): error TS2307: Cannot find module '@samved/schemas' or its corresponding type declarations.
apps/web type-check: src/hooks/useWebSocket.ts(4,42): error TS2307: Cannot find module '@samved/schemas' or its corresponding type declarations.
apps/web type-check: Failed
```

### ROOT CAUSE:
In `packages/schemas/package.json` (and `packages/config/package.json`), the package entry points were configured as:
```json
"main": "./dist/index.js",
"module": "./dist/index.mjs",
"types": "./dist/index.d.ts"
```
Because `dist/` is gitignored, on a fresh checkout in CI `dist/` does not exist prior to compilation. The CI workflow executed `pnpm type-check` before `pnpm build`. Consequently, when TypeScript ran `tsc --noEmit` in `apps/web`, it attempted to resolve `@samved/schemas` types via `./dist/index.d.ts`, which had not yet been generated.

Additionally:
1. In `playwright-e2e` job in `.github/workflows/ci.yml`, `pnpm test:e2e` launches `pnpm start` (`next start -p 3000`) via Playwright's `webServer`, but `pnpm build` was omitted from that job's step sequence. On a clean runner, `.next` would be absent.
2. In the root `package.json`, `"test:backend"` was configured as `"uv run pytest apps/api/tests -v"`, which failed when run from root without specifying `--directory apps/api`, causing pytest to use the root context instead of the configured `apps/api/.venv`.

### AFFECTED FILES:
1. `packages/schemas/package.json`: Main/types entry point pointing to unbuilt `dist/` rather than source `src/index.ts`.
2. `packages/config/package.json`: Main/types entry point pointing to unbuilt `dist/` rather than source `src/index.ts`.
3. `.github/workflows/ci.yml`: Missing `pnpm build` before running Playwright E2E in `playwright-e2e`.
4. `package.json`: Root script `"test:backend"` needed `--directory apps/api` for robust cross-directory execution.

### WHY IT FAILED:
In local development, `pnpm build` had previously been executed, leaving compiled artifacts in `packages/schemas/dist/index.d.ts`, which masked the dependency order issue. In GitHub Actions' clean Linux virtual machine environment, no `dist/` directories existed after `git checkout` and `pnpm install`, immediately surfacing the missing type declarations.

### PROPOSED FIX:
1. Update `packages/schemas/package.json` and `packages/config/package.json` so `"main"` and `"types"` point directly to `./src/index.ts`. Since Next.js has `transpilePackages: ["@samved/schemas", "@samved/config"]` in `next.config.js`, this enables zero-build direct type-checking and hot reloading across the monorepo workspace.
2. Update `.github/workflows/ci.yml` `playwright-e2e` job to run `pnpm build` prior to `pnpm test:e2e`.
3. Update root `package.json` `"test:backend"` to `"uv --directory apps/api run pytest -v"`.
