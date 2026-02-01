from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import ComplaintStatusHistory, AuditLog


def log_status_change(
    db: Session,
    *,
    complaint_id: int,
    status: str,
    note: Optional[str] = None,
    changed_by_admin_id: Optional[int] = None,
    changed_by_user_id: Optional[int] = None,
) -> None:
    db.add(
        ComplaintStatusHistory(
            complaint_id=complaint_id,
            status=status,
            note=note,
            changed_by_admin_id=changed_by_admin_id,
            changed_by_user_id=changed_by_user_id,
        )
    )


def log_audit(
    db: Session,
    *,
    actor_type: str,  # 'admin' or 'user'
    actor_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    meta: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    db.add(
        AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=meta,
            ip=ip,
            user_agent=user_agent,
        )
    )
