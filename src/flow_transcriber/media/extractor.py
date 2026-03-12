from __future__ import annotations
import subprocess
from pathlib import Path
from typing import List

# Formatos de video/audio soportados
SUPPORTED_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".webm", ".flv",  # video
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",  # audio
}

def extract_audio_segments(input_path: Path, out_dir: Path, segment_seconds: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))
    ext = input_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {ext}. Soportados: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    pattern = out_dir / f"{input_path.stem}_part%03d.mp3"
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
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
    created: List[Path] = sorted(out_dir.glob(f"{input_path.stem}_part*.mp3"))
    if not created:
        raise RuntimeError("no mp3 segments created")
    return created
