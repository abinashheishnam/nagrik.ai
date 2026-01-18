from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models import Complaint
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary")
def summary(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    total = db.query(func.count(Complaint.id)).scalar() or 0
    by_status = dict(db.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all())
    by_priority = dict(db.query(Complaint.priority, func.count(Complaint.id)).group_by(Complaint.priority).all())
    by_category = dict(db.query(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category).all())
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
    }
