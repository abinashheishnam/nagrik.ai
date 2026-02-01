from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.social_models import SocialSource

router = APIRouter(prefix="/social", tags=["Social"])

@router.get("/status/{social_source_id}")
def social_status(social_source_id: int, db: Session = Depends(get_db)):
    ss = db.query(SocialSource).filter(SocialSource.id == social_source_id).first()
    if not ss:
        return {"ok": False, "error": "not_found"}
    return {
        "ok": True,
        "id": ss.id,
        "complaint_id": ss.complaint_id,
        "platform": ss.platform,
        "status": ss.status,
        "error": ss.error,
        "updated_at": str(ss.updated_at),
    }
