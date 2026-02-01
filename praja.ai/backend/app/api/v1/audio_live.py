# app/api/v1/routes/audio_live.py

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/audio", tags=["audio"])

# Lazy-loaded model (loads once per process)
_WHISPER = None

def get_model():
    global _WHISPER
    if _WHISPER is None:
        # "base" is fast + decent. You can change to "small" later.
        # device="cpu" works everywhere. If you have CUDA, change device="cuda".
        from faster_whisper import WhisperModel
        _WHISPER = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")



    # Relaxed check: allow any audio type (ignore codecs parameter)
    if not file.content_type.startswith("audio/") and file.content_type != "application/octet-stream":
        raise HTTPException(status_code=415, detail=f"Unsupported content-type: {file.content_type}")

    suffix = ".webm"
    if file.filename:
        lower = file.filename.lower()
        if lower.endswith(".wav"): suffix = ".wav"
        elif lower.endswith(".mp3"): suffix = ".mp3"
        elif lower.endswith(".mp4") or lower.endswith(".m4a"): suffix = ".mp4"
        elif lower.endswith(".ogg"): suffix = ".ogg"
        elif lower.endswith(".webm"): suffix = ".webm"

    # Save upload to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        model = get_model()
        segments, info = model.transcribe(tmp_path, language="en")  # set language=None for auto
        text = " ".join([seg.text.strip() for seg in segments]).strip()

        if not text:
            return {"text": ""}

        return {"text": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

