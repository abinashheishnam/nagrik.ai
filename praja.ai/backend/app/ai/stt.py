# backend/app/ai/stt.py

import os
import tempfile
from typing import Optional

import whisper

# Load Whisper model once (important for performance)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
_model = whisper.load_model(WHISPER_MODEL)


def transcribe_file(file_bytes: bytes, filename: Optional[str] = None) -> str:
    """
    Takes raw uploaded audio bytes and returns transcribed text using Whisper.
    Requires ffmpeg installed on the system.
    """
    suffix = ".webm"
    if filename and "." in filename:
        suffix = os.path.splitext(filename)[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        tmp.write(file_bytes)

    try:
        result = _model.transcribe(tmp_path, language="en")
        return (result.get("text") or "").strip()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
