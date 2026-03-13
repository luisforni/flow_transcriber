from __future__ import annotations

import subprocess
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".webm", ".flv",  # video
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",  # audio
}


def extract_audio_segments(
    input_path: Path, out_dir: Path, segment_seconds: int
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    ext = input_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Formato no soportado: {ext}. "
            f"Soportados: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

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

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")

    created = sorted(out_dir.glob(f"{input_path.stem}_part*.mp3"))
    if not created:
        raise RuntimeError("No se crearon segmentos de audio")

    return created
