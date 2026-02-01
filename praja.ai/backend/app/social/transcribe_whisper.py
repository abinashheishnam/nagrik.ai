from __future__ import annotations

import os
import subprocess
import time
from typing import Optional, Tuple, Dict, Any

# faster-whisper (recommended)
from faster_whisper import WhisperModel


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"command_failed: rc={p.returncode}, cmd={' '.join(cmd)}\n{p.stderr[-2000:]}")


def _to_wav_16k_mono(input_path: str, out_wav: str) -> None:
    """
    Force decode to a Whisper-friendly format.
    """
    _ensure_dir(out_wav)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        "-c:a",
        "pcm_s16le",
        out_wav,
    ]
    _run(cmd)


def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    model_size: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Returns:
      (text or None, meta dict)

    Meta includes:
      engine, model, elapsed_sec, segments, language, language_probability,
      pass_used, errors (if any), wav_path, input_path
    """

    meta: Dict[str, Any] = {
        "engine": "faster-whisper",
        "model": model_size,
        "input_path": audio_path,
        "language": language,
        "segments": 0,
        "elapsed_sec": 0.0,
        "pass_used": None,
        "errors": [],
    }

    start = time.time()

    # 1) Decode to stable wav
    wav_path = os.path.splitext(audio_path)[0] + ".wav"
    try:
        _to_wav_16k_mono(audio_path, wav_path)
        meta["wav_path"] = wav_path
    except Exception as e:
        meta["errors"].append(f"ffmpeg_decode_failed: {e}")
        meta["elapsed_sec"] = round(time.time() - start, 3)
        return None, meta

    # 2) Load model (keep single model per call)
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        meta["errors"].append(f"model_load_failed: {e}")
        meta["elapsed_sec"] = round(time.time() - start, 3)
        return None, meta

    # Helper to run a pass
    def run_pass(pass_name: str, vad_filter: bool, beam_size: int, best_of: int):
        # NOTE: We intentionally try with VAD off first to avoid the "0 segments" trap.
        segments, info = model.transcribe(
            wav_path,
            language=language,
            task="transcribe",
            vad_filter=vad_filter,
            beam_size=beam_size,
            best_of=best_of,
            temperature=0.0,
        )

        # info can be dataclass-like
        meta["detected_language"] = getattr(info, "language", None)
        meta["language_probability"] = getattr(info, "language_probability", None)

        text_parts = []
        seg_count = 0
        for seg in segments:
            seg_count += 1
            if seg.text:
                text_parts.append(seg.text.strip())

        text = " ".join([t for t in text_parts if t]).strip() or None
        return text, seg_count, pass_name

    # PASS A: VAD OFF (most reliable)
    try:
        text, segs, used = run_pass("pass_a_vad_off", vad_filter=False, beam_size=5, best_of=5)
        meta["segments"] = segs
        meta["pass_used"] = used
        if text:
            meta["elapsed_sec"] = round(time.time() - start, 3)
            return text, meta
    except Exception as e:
        meta["errors"].append(f"pass_a_failed: {e}")

    # PASS B: VAD ON but less strict
    try:
        text, segs, used = run_pass("pass_b_vad_on", vad_filter=True, beam_size=5, best_of=5)
        meta["segments"] = segs
        meta["pass_used"] = used
        if text:
            meta["elapsed_sec"] = round(time.time() - start, 3)
            return text, meta
    except Exception as e:
        meta["errors"].append(f"pass_b_failed: {e}")

    # PASS C: more exploratory decode
    try:
        text, segs, used = run_pass("pass_c_wide_decode", vad_filter=False, beam_size=1, best_of=1)
        meta["segments"] = segs
        meta["pass_used"] = used
        if text:
            meta["elapsed_sec"] = round(time.time() - start, 3)
            return text, meta
    except Exception as e:
        meta["errors"].append(f"pass_c_failed: {e}")

    meta["elapsed_sec"] = round(time.time() - start, 3)
    return None, meta
