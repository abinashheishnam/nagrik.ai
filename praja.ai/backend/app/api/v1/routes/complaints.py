from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.db.models import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintOut
from app.auth.dependencies import get_current_user
from app.ai.pipeline import enrich

# IMPORTANT: no /api/v1 here. main.py adds /api/v1 prefix.
router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ai = enrich(payload.title, payload.description, address=payload.address)

    c = Complaint(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        category="",
        priority=ai["ai_priority"],
        status="Open",
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        source="web",
        language=ai["language"],
        ai_category=ai["ai_category"],
        ai_priority=ai["ai_priority"],
        ai_confidence=ai["ai_confidence"],
        ai_summary=ai["ai_summary"],
        ai_keywords=ai["ai_keywords"],
        ai_rationale=ai["ai_rationale"],
        final_category="",
        final_priority=""
    )

    db.add(c)
    db.commit()
    db.refresh(c)

    # make sure response has user without needing another query
    c.user = user
    return c


@router.get("", response_model=list[ComplaintOut])
def get_all_complaints(db: Session = Depends(get_db)):
    return (
        db.query(Complaint)
        .options(joinedload(Complaint.user))
        .order_by(Complaint.id.desc())
        .all()
    )


@router.get("/my", response_model=list[ComplaintOut])
def my_complaints(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return (
        db.query(Complaint)
        .options(joinedload(Complaint.user))
        .filter(Complaint.user_id == user.id)
        .order_by(Complaint.id.desc())
        .all()
    )
