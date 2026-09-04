# SAMVED Docker Runbook

This runbook details how to validate, run, and manage SAMVED using Docker and Docker Compose.

---

## 1. Docker Compose Configuration

The SAMVED multi-service stack is orchestrated with Docker Compose:
- **`postgres`**: PostgreSQL relational database.
- **`redis`**: High-performance in-memory cache and pub/sub.
- **`api`**: FastAPI backend service exposing REST, WebSocket, and Telephony streams on port `8000`.
- **`web`**: Next.js operator frontend on port `3000`.

### 1.1 Validating Compose Syntax
```bash
docker compose config
```
Ensures configuration syntax and environment variable interpolations are valid without errors.

---

## 2. Running the Full Stack

### 2.1 Starting Services
```bash
# Start all containers in detached mode
docker compose up -d

# Check status of containers
docker compose ps
```

### 2.2 Inspecting Logs
```bash
# Follow logs across all containers
docker compose logs -f

# Follow logs for the FastAPI backend only
docker compose logs -f api

# Follow logs for the web application
docker compose logs -f web
```

### 2.3 Stopping Services
```bash
# Gracefully stop containers
docker compose down

# Stop and wipe volumes (database reset)
docker compose down -v
```

---

## 3. Running Automated Tests via Docker

You can execute the test suite inside the containerized environment:

```bash
# Run pytest inside the api container
docker compose run --rm api uv run pytest -v

# Run Playwright e2e tests inside the web container
docker compose run --rm web pnpm --filter @samved/web test:e2e
```
