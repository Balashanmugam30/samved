from fastapi import APIRouter
from app.api.v1.calls import router as calls_router
from app.api.v1.health import router as health_router
from app.api.v1.telephony import telephony_router
from app.api.v1.safety import router as safety_router
from app.api.v1.svi import router as svi_router
from app.api.v1.acoustic import router as acoustic_router
from app.api.v1.adaptive import router as adaptive_router
from app.api.v1.operator import router as operator_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(telephony_router)
api_v1_router.include_router(calls_router, prefix="/calls")
api_v1_router.include_router(safety_router)
api_v1_router.include_router(svi_router)
api_v1_router.include_router(acoustic_router)
api_v1_router.include_router(adaptive_router)
api_v1_router.include_router(operator_router)


