from fastapi import APIRouter

# IMPORTANT: no prefix here. main.py mounts this under /api/v1
router = APIRouter()

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.complaints import router as complaints_router
from app.api.v1.routes.admin_complaints import router as admin_complaints_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.ai_draft import router as ai_draft_router
from app.api.v1.routes.whatsapp import router as whatsapp_router
from app.api.v1.audio_live import router as audio_live_router
from app.api.v1.routes.social_intake import router as social_router
from app.api.v1.routes.social_status import router as social_status_router
from app.api.v1.routes.social_source import router as social_source_router
from app.api.v1.routes.evidence import router as evidence_router

router.include_router(health_router)
router.include_router(complaints_router)
router.include_router(admin_complaints_router)
router.include_router(analytics_router)
router.include_router(ai_draft_router)
router.include_router(whatsapp_router)
router.include_router(audio_live_router)
router.include_router(social_router)
router.include_router(social_status_router)
router.include_router(social_source_router)
router.include_router(evidence_router)

