from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Complaint, User
from app.schemas.complaint import ComplaintOut
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/v1/admin/complaints", tags=["admin-complaints"])

@router.get("", response_model=list[ComplaintOut])
def all_complaints(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    return db.query(Complaint).order_by(Complaint.id.desc()).all()

@router.get("/{complaint_id}")
def complaint_detail(complaint_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    u = db.query(User).filter(User.id == c.user_id).first()

    return {
        "complaint": {
            "id": c.id,
            "user_id": c.user_id,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "priority": c.priority,
            "status": c.status,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "address": c.address,
            "created_at": c.created_at.isoformat()
        },
        "user": {
            "id": u.id if u else None,
            "full_name": u.full_name if u else "",
            "phone": u.phone if u else "",
            "email": u.email if u else ""
        }
    }
