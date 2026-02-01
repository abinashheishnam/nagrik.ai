from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func

from app.db.session import Base


class SocialSource(Base):
    __tablename__ = "social_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(20), nullable=False, index=True)

    # New production fields (already added in DB)
    platform_id = Column(String(80), nullable=True)
    url = Column(String(700), nullable=False)
    canonical_url = Column(String(700), nullable=True)
    payload_hash = Column(String(64), nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, nullable=True)

    status = Column(String(20), nullable=False, default="QUEUED", index=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ExtractedSignals(Base):
    __tablename__ = "extracted_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)

    # Critical: exists in DB (nullable) — needed for per-source evidence
    social_source_id = Column(Integer, nullable=True, index=True)

    post_text = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True)
    entities = Column(JSON, nullable=True)
    source_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())


class AIInferenceRun(Base):
    __tablename__ = "ai_inference_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)

    model_name = Column(String(50), nullable=False, index=True)
    model_version = Column(String(50), nullable=False, default="v0")

    output = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    requires_review = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
