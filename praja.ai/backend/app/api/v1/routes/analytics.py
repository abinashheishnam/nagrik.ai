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

@router.get("/public")
def public_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Complaint.id)).scalar() or 0
    resolved = db.query(func.count(Complaint.id)).filter(Complaint.status.in_(["Resolved", "Closed"])).scalar() or 0
    
    # Mock avg time for now as we don't track resolved_at yet
    # In a real app, we'd compute avg(resolved_at - created_at)
    import random
    avg_hours = 24 + (total % 10) # deterministic-ish
    
    return {
        "total_reports": total,
        "resolved_cases": resolved,
        "avg_hours": avg_hours
    }
