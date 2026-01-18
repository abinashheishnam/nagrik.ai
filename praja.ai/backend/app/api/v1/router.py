from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.complaints import router as complaints_router
from app.api.v1.routes.admin_complaints import router as admin_complaints_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.ai_draft import router as ai_draft_router
from app.api.v1.routes.whatsapp import router as whatsapp_router

# IMPORTANT:
# No prefix here. We'll mount this router under /api/v1 in main.py.
router = APIRouter()

router.include_router(health_router)
router.include_router(complaints_router)
router.include_router(admin_complaints_router)
router.include_router(analytics_router)
router.include_router(ai_draft_router)
router.include_router(whatsapp_router)
