from __future__ import annotations
from datetime import datetime, timezone

def build_header(template: str, *, file_name: str, source_name: str, language: str | None, segment_index: int, segment_count: int) -> str:
    now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    data = {
        "file_name": file_name,
        "source_name": source_name,
        "language": language or "auto",
        "now_iso": now_iso,
        "segment_index": segment_index,
        "segment_count": segment_count,
    }
    return template.format(**data)
