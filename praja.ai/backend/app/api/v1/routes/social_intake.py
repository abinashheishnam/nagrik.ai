from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Complaint, AuditLog
from app.db.social_models import SocialSource
from app.schemas.social import SocialIntakeRequest, SocialIntakeResponse
from app.utils.social_platform import detect_platform
from app.utils.queue import get_queue

# ✅ IMPORTANT: enqueue callable, not string
from app.workers.social_jobs import process_social_source

router = APIRouter(prefix="/social", tags=["Social"])


@router.post("/intake", response_model=SocialIntakeResponse)
def social_intake(
    payload: SocialIntakeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    platform = detect_platform(str(payload.url))

    # Use provided user_id or default to 1 (system/anonymous)
    user_id = payload.user_id if payload.user_id else 1

    c = Complaint(
        user_id=user_id,
        title="Social media report",
        description=f"Social link submitted: {payload.url}",
        source="social",
        status="PENDING_AI",
        category="General",
        priority="Medium",
        ai_keywords="",
        ai_summary="",
        ai_rationale="",
    )
    db.add(c)
    db.flush()

    ss = SocialSource(
        complaint_id=c.id,
        platform=platform,
        url=str(payload.url),
        status="QUEUED",
    )
    db.add(ss)
    db.flush()

    # ✅ Enqueue background processing (deterministic queue + callable)
    q = get_queue("social")
    job = q.enqueue(
        process_social_source,
        ss.id,
        job_timeout=1200,   # 20 min hard cap for the whole job
        result_ttl=0,
        failure_ttl=86400,  # keep failed jobs 1 day for debugging
    )

    db.add(
        AuditLog(
            actor_type="user",
            actor_id=user_id,
            action="social_intake_created",
            entity_type="complaint",
            entity_id=c.id,
            meta={"platform": platform, "url": str(payload.url), "rq_job_id": getattr(job, "id", None)},
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )

    db.commit()

    return SocialIntakeResponse(
        complaint_id=c.id,
        social_source_id=ss.id,
        platform=platform,
        status=ss.status,
    )
