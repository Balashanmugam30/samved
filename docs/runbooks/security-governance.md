# SAMVED Runbook: Security & Governance Operations

## 1. Quick Verification Commands

### 1.1 Run Backend Security Test Suite
```bash
# Run all Phase 15 security regression tests
apps/api/.venv/Scripts/pytest apps/api/tests/test_security_*.py -v

# Run entire backend suite (417+ tests)
apps/api/.venv/Scripts/pytest apps/api/tests
```

### 1.2 Run Playwright E2E Security Tests
```bash
# Run security console browser tests
pnpm --filter @samved/web test:e2e e2e/security-governance.spec.ts
```

### 1.3 Verify Audit Trail Integrity via CLI / cURL
```bash
curl -s http://localhost:8000/v1/security/audit/verify \
  -H "X-User-Role: SUPERVISOR" \
  -H "X-User-Id: usr-supervisor-01"
```

### 1.4 Test Indian PII Redaction Pipeline via cURL
```bash
curl -X POST http://localhost:8000/v1/security/pii/redact \
  -H "Content-Type: application/json" \
  -H "X-User-Role: OPERATOR" \
  -d '{"text": "Caller mobile is +91-9876543210 and Aadhaar is 2345 6789 0123."}'
```

## 2. Web Console Navigation
- **Security & Governance Dashboard**: Navigate to `http://localhost:3000/security` to view active controls, switch roles dynamically, and run live PII sanitization.
- **Audit Trail Explorer**: Navigate to `http://localhost:3000/audit` to view SHA-256 chained log entries and trigger real-time integrity verification.
