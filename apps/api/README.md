# SAMVED — API Service (`apps/api`)

FastAPI backend application powering the SAMVED victim triage and response intelligence platform.

## Features
- **Endpoints**: `/health`, `/ready`, `/version`, and `/ws` (Realtime WebSocket).
- **Architecture**: Structured request IDs, zero secret logging, typed configuration, and provider adapters.
- **Operating Modes**: Explicit `DEV`, `SIMULATION`, and `LIVE` execution modes.
- **Tests**: Comprehensive pytest test suite covering unit, WebSocket, configuration, error handling, and provider mocks.
