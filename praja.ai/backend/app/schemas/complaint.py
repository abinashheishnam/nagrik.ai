from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.auth import UserOut

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    description: str = Field(..., min_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str = ""

class ComplaintOut(BaseModel):
    id: int
    user_id: int
    user: Optional[UserOut] = None  # user details
    title: str
    description: str

    category: str
    priority: str
    status: str

    latitude: Optional[float]
    longitude: Optional[float]
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

    created_at: datetime

    class Config:
        from_attributes = True
