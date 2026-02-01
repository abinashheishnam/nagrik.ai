import os
import subprocess
from pathlib import Path

whisper_model = None

def _run(cmd: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return r.returncode, r.stdout, r.stderr

def _has_ffmpeg() -> bool:
    try:
        code, out, err = _run(["ffmpeg", "-version"])
        return code == 0
    except Exception:
        return False

def _load_whisper():
    global whisper_model
    if whisper_model is not None:
        return whisper_model

    try:
        import whisper
    except Exception as e:
        print("[STT] whisper not installed or import failed:", e)
        return None

    model_name = os.getenv("WHISPER_MODEL", "base")
    try:
        whisper_model = whisper.load_model(model_name)
        print(f"[STT] Whisper model loaded: {model_name}")
        return whisper_model
    except Exception as e:
        print("[STT] Failed to load whisper model:", e)
        return None

def _ffmpeg_to_16k_mono_wav(src_path: str) -> tuple[str | None, str]:
    """
    Convert input audio to 16kHz mono WAV.
    Returns (wav_path, debug_msg). wav_path can be None on failure.

    IMPORTANT:
    - Never overwrite the input file (especially if it's already .wav).
    """
    src = Path(src_path)
    if not src.exists():
        return None, "source file does not exist"

    if not _has_ffmpeg():
        return None, "ffmpeg not found on PATH"

    # Always output to a NEW file to avoid overwriting input
    wav_path = src.with_name(src.stem + "_16k.wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        str(wav_path)
    ]

    try:
        code, out, err = _run(cmd)
        if code != 0:
            msg = err.strip().splitlines()[-15:]
            return None, "ffmpeg failed: " + "\n".join(msg)

        if not wav_path.exists() or wav_path.stat().st_size < 1000:
            return None, "ffmpeg produced empty/too-small wav"

        return str(wav_path), "ok"
    except Exception as e:
        return None, f"ffmpeg exception: {e}"

def transcribe_audio(audio_path: str) -> str:
    """
    Returns transcript text.
    Pipeline:
    - Convert to 16k mono wav (new file, never overwrite input)
    - Run Whisper on wav
    """
    if not audio_path or not os.path.exists(audio_path):
        print("[STT] audio_path missing:", audio_path)
        return ""

    model = _load_whisper()
    if model is None:
        print("[STT] model is None (whisper missing or failed to load)")
        return ""

    wav_path, debug = _ffmpeg_to_16k_mono_wav(audio_path)
    if not wav_path:
        print("[STT] Could not convert audio -> wav:", debug)
        return ""

    try:
        result = model.transcribe(
            wav_path,
            initial_prompt="This audio may contain a mix of English and Hindi (Hinglish). Transcribe it exactly as spoken."
        )
        text = (result.get("text") or "").strip()
        if not text:
            print("[STT] Whisper returned empty transcript.")
        return text
    except Exception as e:
        print("[STT] whisper transcribe error:", e)
        return ""
    finally:
        try:
            Path(wav_path).unlink(missing_ok=True)
        except Exception as e:
            print("[STT] cleanup failed:", e)
