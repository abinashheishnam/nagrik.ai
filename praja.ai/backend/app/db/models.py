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
