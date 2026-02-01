from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.auth import UserOut


class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str = Field(default="", max_length=255)


class ComplaintOut(BaseModel):
    id: int
    user_id: int

    title: str
    description: str

    category: str
    priority: str
    status: str

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str

    source: str
    language: str

    ai_category: str
    ai_priority: str
    ai_confidence: float
    ai_summary: str
    ai_keywords: str
    ai_rationale: str

    final_category: str
    final_priority: str

    is_emergency: int
    emergency_type: str
    emergency_confirmed: int
    emergency_call_status: str

    created_at: datetime
    is_viewed_by_admin: bool = False

    # Optional nested user payload (your admin UI sometimes expects it)
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True


class ComplaintStatusHistoryOut(BaseModel):
    id: int
    complaint_id: int
    status: str
    note: Optional[str] = None
    created_at: datetime
    changed_by_admin_id: Optional[int] = None
    changed_by_user_id: Optional[int] = None

    class Config:
        from_attributes = True
