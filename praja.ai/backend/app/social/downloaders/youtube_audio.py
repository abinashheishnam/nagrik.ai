from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from typing import Tuple, Dict


def _which(bin_name: str) -> str:
    p = shutil.which(bin_name)
    if not p:
        raise FileNotFoundError(f"{bin_name} not found in PATH")
    return p


def download_youtube_audio(url: str, out_dir: str, video_id: str | None = None) -> Tuple[str, Dict]:
    """
    Production-safe YouTube audio fetch:
    - hard timeouts (subprocess.run timeout)
    - limits to first 60 seconds to avoid long jobs / hangs
    - returns (audio_path, metadata)

    Requires: yt-dlp, ffmpeg
    """
    yt_dlp = _which("yt-dlp")
    _which("ffmpeg")  # yt-dlp relies on it for audio extraction

    os.makedirs(out_dir, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = (video_id or "yt") + "_" + stamp
    # yt-dlp will create .mp3 due to --audio-format mp3
    out_tmpl = os.path.join(out_dir, base + ".%(ext)s")
    expected_mp3 = os.path.join(out_dir, base + ".mp3")

    # Key idea:
    #  - download only first 60 seconds
    #  - keep retries small
    #  - enforce ipv4 (some networks stall on ipv6)
    cmd = [
        yt_dlp,
        "--no-playlist",
        "--force-ipv4",
        "--retries", "2",
        "--fragment-retries", "2",
        "--socket-timeout", "15",
        "--concurrent-fragments", "2",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        # Limit to first 60 seconds (huge stability win)
        "--download-sections", "*00:00-00:01:00",
        "-o", out_tmpl,
        url,
    ]

    meta: Dict = {
        "cmd": " ".join(cmd),
        "out_dir": out_dir,
        "output_template": out_tmpl,
        "expected_mp3": expected_mp3,
    }

    try:
        # Hard timeout: yt-dlp MUST finish quickly or we bail
        # 90 seconds is generous for a 60s audio segment.
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        meta["returncode"] = r.returncode
        meta["stdout_tail"] = (r.stdout or "")[-800:]
        meta["stderr_tail"] = (r.stderr or "")[-800:]

        if r.returncode != 0:
            raise RuntimeError(f"yt-dlp failed rc={r.returncode}")

        if not os.path.exists(expected_mp3):
            # Sometimes extension differs; find any produced audio file
            produced = []
            for fn in os.listdir(out_dir):
                if fn.startswith(base + "."):
                    produced.append(os.path.join(out_dir, fn))
            meta["produced_files"] = produced
            if produced:
                return produced[0], meta
            raise FileNotFoundError("yt-dlp succeeded but output file not found")

        return expected_mp3, meta

    except subprocess.TimeoutExpired as e:
        meta["timeout"] = "yt-dlp_timeout_90s"
        meta["stderr_tail"] = (getattr(e, "stderr", "") or "")[-800:]
        meta["stdout_tail"] = (getattr(e, "stdout", "") or "")[-800:]
        raise RuntimeError("yt-dlp timeout (90s)") from e
