import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.realtime.websocket_router import ws_router
from app.realtime.telephony_ws_router import telephony_ws_router

settings = get_settings()
logger = setup_logging(
    log_level=settings.LOG_LEVEL,
    structured=settings.ENABLE_STRUCTURED_JSON_LOGS,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [ENV: {settings.APP_ENV}, MODE: {settings.APP_MODE}]"
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title="SAMVED API",
    description="AI-assisted victim triage, safety assessment, and response intelligence platform for NHAA 14566",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Correlation ID & Latency Middleware
app.add_middleware(RequestContextMiddleware)

# 3. Global Exception Handlers
register_error_handlers(app)

# 4. Include Direct Health Endpoints (Root)
app.include_router(health_router)

# 5. Include Versioned API Routes (/v1)
app.include_router(api_v1_router)

# 6. Include Realtime WebSocket Gateway (/ws)
app.include_router(ws_router)

# 7. Include Realtime Telephony Media Stream Gateway (/ws/telephony/exotel)
app.include_router(telephony_ws_router)
