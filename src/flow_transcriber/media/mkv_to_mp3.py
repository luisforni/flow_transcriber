from __future__ import annotations
import subprocess
from pathlib import Path
from typing import List

def extract_audio_segments(mkv_path: Path, out_dir: Path, segment_seconds: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not mkv_path.exists():
        raise FileNotFoundError(str(mkv_path))
    pattern = out_dir / f"{mkv_path.stem}_part%03d.mp3"
    cmd = [
        "ffmpeg",
        "-i", str(mkv_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        "-ar", "44100",
        "-f", "segment",
        "-segment_time", str(segment_seconds),
        "-reset_timestamps", "1",
        str(pattern),
        "-y",
    ]
    rr = subprocess.run(cmd, capture_output=True, text=True)
    if rr.returncode != 0:
        raise RuntimeError(rr.stderr.strip() or "ffmpeg failed")
    created: List[Path] = sorted(out_dir.glob(f"{mkv_path.stem}_part*.mp3"))
    if not created:
        raise RuntimeError("no mp3 segments created")
    return created
