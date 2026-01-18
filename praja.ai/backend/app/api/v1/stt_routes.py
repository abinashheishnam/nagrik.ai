# backend/app/api/v1/stt_routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.ai.stt import transcribe_file

router = APIRouter(prefix="/api/v1/stt", tags=["STT"])


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    text = transcribe_file(audio_bytes, file.filename)
    return {"text": text}
