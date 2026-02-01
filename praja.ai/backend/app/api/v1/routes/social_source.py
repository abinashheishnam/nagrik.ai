from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.social_models import SocialSource, ExtractedSignals

router = APIRouter(prefix="/social", tags=["Social"])


@router.get("/source/{social_source_id}")
def get_social_source_details(
    social_source_id: int,
    db: Session = Depends(get_db)
):
    # 1. Fetch SocialSource
    source = db.query(SocialSource).filter(SocialSource.id == social_source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Social source not found")

    # 2. Fetch ExtractedSignals (linked via social_source_id)
    signals = (
        db.query(ExtractedSignals)
        .filter(ExtractedSignals.social_source_id == social_source_id)
        .first()
    )

    extracted_data = {}
    if signals:
        post_text = signals.post_text or ""
        transcript = signals.transcript or ""
        ocr_text = signals.ocr_text or ""

        extracted_data = {
            "post_text_preview": post_text[:1200],
            "post_text_len": len(post_text),
            "transcript_preview": transcript[:1200],
            "transcript_len": len(transcript),
            "ocr_text_preview": ocr_text[:1200],
            "ocr_text_len": len(ocr_text),
            "entities": signals.entities,
            "source_metadata": signals.source_metadata,
        }

    return {
        "id": source.id,
        "complaint_id": source.complaint_id,
        "platform": source.platform,
        "platform_id": source.platform_id,
        "url": source.url,
        "status": source.status,
        "error": source.error,
        "extracted": extracted_data,
    }
