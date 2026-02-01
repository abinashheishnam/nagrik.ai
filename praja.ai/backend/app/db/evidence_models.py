from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base

class ComplaintEvidence(Base):
    __tablename__ = "complaint_evidence"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)

    evidence_type = Column(String(20), nullable=False)  # audio|image|video|doc
    file_path = Column(String(700), nullable=False)
    mime_type = Column(String(80), nullable=False)

    file_size = Column(Integer, nullable=False, default=0)
    original_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
