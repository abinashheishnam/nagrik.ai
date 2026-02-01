from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaints = relationship("Complaint", back_populates="user")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="OFFICER")  # ✅ ADD THIS
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    # Citizen input
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="General")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(30), default="Open")

    # Location
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    address: Mapped[str] = mapped_column(String(255), default="")

    # Channel
    source: Mapped[str] = mapped_column(String(20), default="web")
    language: Mapped[str] = mapped_column(String(10), default="en")

    # Emergency handling
    is_emergency: Mapped[int] = mapped_column(Integer, default=0)
    emergency_type: Mapped[str] = mapped_column(String(30), default="")
    emergency_confirmed: Mapped[int] = mapped_column(Integer, default=0)
    emergency_call_status: Mapped[str] = mapped_column(String(30), default="")

    # AI outputs
    ai_category: Mapped[str] = mapped_column(String(80), default="General")
    ai_priority: Mapped[str] = mapped_column(String(20), default="Medium")
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    ai_keywords: Mapped[str] = mapped_column(Text, default="")
    ai_rationale: Mapped[str] = mapped_column(Text, default="")

    # Human-in-the-loop override
    final_category: Mapped[str] = mapped_column(String(80), default="")
    final_priority: Mapped[str] = mapped_column(String(20), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Read Receipt
    is_viewed_by_admin: Mapped[bool] = mapped_column(Integer, default=False) # Helper: Using Integer for boolean compatibility if needed, but SQLAlchemy Bool is fine. Sticking to mapped_column defaults.

    user = relationship("User", back_populates="complaints")


class WhatsAppSession(Base):
    """
    Conversational onboarding + intake state for WhatsApp assistant.
    Backed by MySQL table: whatsapp_sessions
    """
    __tablename__ = "whatsapp_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(30))

    # onboarding
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    otp_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    otp_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # draft complaint
    issue_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func


class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False)
    note = Column(Text, nullable=True)

    changed_by_admin_id = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    changed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class ComplaintAssignment(Base):
    __tablename__ = "complaint_assignments"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)

    department = Column(String(80), nullable=False, index=True)
    assigned_to_admin_id = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    due_at = Column(DateTime, nullable=True, index=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    actor_type = Column(String(10), nullable=False)   # 'admin' or 'user'
    actor_id = Column(Integer, nullable=False)

    action = Column(String(60), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=False)

    meta = Column(JSON, nullable=True)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
from app.db.social_models import SocialSource, ExtractedSignals, AIInferenceRun  # noqa: F401

# Load evidence models
from app.db.evidence_models import ComplaintEvidence  # noqa: F401

# Load evidence models
from app.db.evidence_models import ComplaintEvidence  # noqa: F401
