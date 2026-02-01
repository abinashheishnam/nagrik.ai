import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.evidence_models import ComplaintEvidence
from app.db.models import Complaint
from fastapi.responses import FileResponse

router = APIRouter(prefix="/evidence", tags=["Evidence"])

STORAGE_DIR = Path("storage/complaints")

@router.api_route("/audio/{evidence_id}", methods=["GET", "HEAD"])
def get_audio(evidence_id: int, db: Session = Depends(get_db)):
    ev = db.query(ComplaintEvidence).filter(ComplaintEvidence.id == evidence_id).first()
    if not ev or ev.evidence_type != "audio":
        raise HTTPException(status_code=404, detail="Not found")

    # TODO: enforce admin auth here
    return FileResponse(ev.file_path, media_type=ev.mime_type, filename=ev.original_name or "audio")

@router.get("/complaints/{complaint_id}")
def list_evidence(complaint_id: int, db: Session = Depends(get_db)):
    rows = db.query(ComplaintEvidence).filter(ComplaintEvidence.complaint_id == complaint_id).all()
    return [{
        "id": r.id,
        "type": r.evidence_type,
        "mime": r.mime_type,
        "name": r.original_name,
        "size": r.file_size,
    } for r in rows]


@router.post("/complaints/{complaint_id}/audio")
async def upload_complaint_audio(
    complaint_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Validate complaint exists
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Validate audio (curl may send octet-stream; allow by extension fallback)
    suffix = Path(file.filename or "").suffix.lower()
    allowed_ext = {".wav", ".mp3", ".m4a", ".ogg", ".webm"}

    is_audio_mime = bool(file.content_type) and file.content_type.startswith("audio/")
    is_audio_ext = suffix in allowed_ext

    if not (is_audio_mime or is_audio_ext):
        raise HTTPException(status_code=400, detail="Only audio uploads allowed")

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in [".wav", ".mp3", ".m4a", ".ogg", ".webm"]:
        # still allow, but normalize extension if missing
        ext = ".wav" if file.content_type == "audio/wav" else ext or ".audio"

    safe_name = f"{complaint_id}_{uuid.uuid4().hex}{ext}"
    save_path = STORAGE_DIR / safe_name

    # Save file
    data = await file.read()
    save_path.write_bytes(data)

    ev = ComplaintEvidence(
        complaint_id=complaint_id,
        evidence_type="audio",
        file_path=str(save_path),
        mime_type=file.content_type,
        file_size=len(data),
        original_name=file.filename,
    )
    db.add(ev)
    db.commit()

    return {
        "ok": True,
        "evidence_id": ev.id,
        "complaint_id": complaint_id,
        "mime_type": ev.mime_type,
        "file_size": ev.file_size,
    }
