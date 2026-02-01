import os
import json
import time
import uuid
from fastapi import HTTPException

LIVE_AUDIO_DIR = os.getenv("PRAJA_LIVE_AUDIO_DIR", "storage/live_audio")
MAX_AUDIO_MB = int(os.getenv("PRAJA_MAX_AUDIO_MB", "25"))

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _session_dir(session_id: str) -> str:
    return os.path.join(LIVE_AUDIO_DIR, session_id)

def _meta_path(session_id: str) -> str:
    return os.path.join(_session_dir(session_id), "meta.json")

def _audio_path(session_id: str) -> str:
    return os.path.join(_session_dir(session_id), "audio.webm")

def start_session(complaint_id: int, user_id: int, mime: str) -> str:
    _ensure_dir(LIVE_AUDIO_DIR)
    session_id = uuid.uuid4().hex
    sdir = _session_dir(session_id)
    _ensure_dir(sdir)

    meta = {
        "session_id": session_id,
        "complaint_id": complaint_id,
        "user_id": user_id,
        "mime": mime,
        "created_at": int(time.time()),
        "bytes": 0,
        "finished": False,
    }
    with open(_meta_path(session_id), "w", encoding="utf-8") as f:
        json.dump(meta, f)

    open(_audio_path(session_id), "ab").close()
    return session_id

def load_meta(session_id: str) -> dict:
    mp = _meta_path(session_id)
    if not os.path.exists(mp):
        raise HTTPException(status_code=404, detail="Live audio session not found")
    with open(mp, "r", encoding="utf-8") as f:
        return json.load(f)

def save_meta(session_id: str, meta: dict) -> None:
    with open(_meta_path(session_id), "w", encoding="utf-8") as f:
        json.dump(meta, f)

def append_chunk(session_id: str, chunk_bytes: bytes) -> dict:
    meta = load_meta(session_id)
    if meta.get("finished"):
        raise HTTPException(status_code=400, detail="Session already finished")

    new_total = int(meta.get("bytes", 0)) + len(chunk_bytes)
    if new_total > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Audio too large (>{MAX_AUDIO_MB}MB)")

    ap = _audio_path(session_id)
    with open(ap, "ab") as f:
        f.write(chunk_bytes)

    meta["bytes"] = new_total
    save_meta(session_id, meta)
    return meta

def finish_session(session_id: str) -> dict:
    meta = load_meta(session_id)
    meta["finished"] = True
    meta["finished_at"] = int(time.time())
    save_meta(session_id, meta)
    meta["audio_path"] = _audio_path(session_id)
    return meta
