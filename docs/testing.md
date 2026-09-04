# SAMVED — Testing Strategy & Quality Assurance

## 1. Testing Pyramid
SAMVED enforces an integrated, multi-tier testing strategy ensuring that real-time telephonic and triage operations function reliably without regressions.

```
       / \
      / E2E \       Playwright Browser Smoke Tests (Desktop & Mobile)
     /-------\
    / Contract\     Producer-to-Consumer Event Envelope WebSocket Validation
   /-----------\
  / Integration \   Multi-provider Mock Streaming Pipeline Tests
 /---------------\
/   Unit Tests    \ Pytest (API, Config, Middleware, Models, Schemas)
-------------------
```

---

## 2. Test Execution Commands

### Backend Pytest Suite
Runs 18 unit, configuration, health, and WebSocket tests:
```bash
cd apps/api
uv run pytest -v
```

### End-to-End Contract Testing
Validates that events created by a producer strictly adhere to `EventEnvelope` and `SVIUpdatedPayload`, traverse the WebSocket gateway, and deserialize properly at the consumer:
```bash
uv run pytest apps/api/tests/test_contract_flow.py -v
```

### Playwright E2E Smoke Tests
Executes headless browser tests verifying application rendering, status telemetry, DEV mode badging, and navigation:
```bash
cd apps/web
pnpm test:e2e
```

---

## 3. Playwright Validation Details
The Playwright test suite (`apps/web/e2e/smoke.spec.ts`) automatically validates:
1. **Application Shell & Identity**: Confirms page title, helpline header (`14566`), and SIH problem statement (`26093`).
2. **Honest Operational Status**: Verifies that backend, realtime gateway, and mock provider states display accurately without manufactured metrics.
3. **Multi-Viewport Responsiveness**: Validates layout integrity on Desktop Chrome (1280x720) and Mobile (Pixel 5: 375x667).
4. **Console Cleanliness**: Asserts zero uncaught JavaScript console errors during application lifecycle.
