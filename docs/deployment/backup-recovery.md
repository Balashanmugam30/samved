# SAMVED — Backup, Disaster Recovery & Evidentiary Integrity Runbook

**System Version:** `v1.0.0-sih2026`  
**Classification:** Infrastructure & Data Governance Runbook

---

## 1. Database Backup & Disaster Recovery (PostgreSQL 16)

SAMVED persists cases, caller entities, graph relations, and audit records in PostgreSQL.

### Automated Daily Dump (Hot Backup)
To perform a consistent, non-blocking backup of the SAMVED database:

```bash
# Execute pg_dump inside container
docker exec -t samved-postgres pg_dump -U postgres -d samved_dev -F c -b -v -f /var/lib/postgresql/data/samved_backup_$(date +%Y%m%d_%H%M%S).dump

# Copy backup off-host to secure storage
docker cp samved-postgres:/var/lib/postgresql/data/samved_backup_latest.dump ./backups/
```

### Complete Database Restoration
To restore the database from an existing dump file:

```bash
# Stop application services to prevent concurrent writes
docker compose stop api web

# Drop existing connections and restore
docker exec -i samved-postgres pg_restore -U postgres -d samved_dev --clean --if-exists /var/lib/postgresql/data/samved_backup_latest.dump

# Restart application services
docker compose start api web
```

---

## 2. In-Memory State & Cache Recovery (Redis 7)

Redis maintains active telephony audio frames, real-time rate limiter buckets, and WebSocket session tokens.

### Point-in-Time Snapshot (RDB)
Redis automatically persists snapshots to `/data/dump.rdb` based on the standard configuration:
* `save 900 1` (after 900s if at least 1 key changed)
* `save 300 10` (after 300s if at least 10 keys changed)
* `save 60 10000` (after 60s if at least 10000 keys changed)

To force an immediate synchronous snapshot before maintenance:
```bash
docker exec -t samved-redis redis-cli BGSAVE
```

---

## 3. Cryptographic Audit Chain Verification (Non-Repudiation)

Following any database restoration or forensic review, verify that historical audit records have not been tampered with or corrupted:

```bash
# Execute API audit chain verification endpoint
curl -s http://localhost:8000/v1/security/audit/verify | jq .
```

Expected Response:
```json
{
  "is_valid": true,
  "message": "Cryptographic audit chain verified successfully across all entries.",
  "total_records": 48,
  "genesis_hash_verified": true,
  "latest_hash": "a9f8b2c4e1d3570298a4bb11cc33ef928174aa9384729012384950ab9c02d184"
}
```

If any row in the `security_audit_log` table was modified or deleted, `is_valid` will evaluate to `false` with the exact index of the broken block.
