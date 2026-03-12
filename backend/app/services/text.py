from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def build_header(
    template: str,
    *,
    file_name: str,
    source_name: str,
    language: str | None,
    segment_index: int,
    segment_count: int,
) -> str:
    now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    data = {
        "file_name": file_name,
        "source_name": source_name,
        "language": language or "auto",
        "now_iso": now_iso,
        "segment_index": segment_index,
        "segment_count": segment_count,
    }
    try:
        return template.format(**data)
    except KeyError:
        return template


def concat_and_chunk_with_header(
    txt_files: list[Path],
    out_dir: Path,
    max_chars: int,
    header_template: str,
    language: str | None,
    source_name: str,
    output_ext: str = "txt",
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(txt_files)
    if not files:
        return []

    source_file_name = Path(source_name).name
    header = build_header(
        header_template,
        file_name=source_file_name,
        source_name=source_file_name,
        language=language,
        segment_index=1,
        segment_count=len(files),
    )

    big_text = header + files[0].read_text(encoding="utf-8") + "\n"
    for p in files[1:]:
        big_text += p.read_text(encoding="utf-8") + "\n"

    ext = output_ext.lstrip(".")
    parts: list[Path] = []
    for i, start in enumerate(range(0, len(big_text), max_chars), 1):
        chunk = big_text[start : start + max_chars]
        out_path = out_dir / f"{Path(source_name).stem}_final_part{i:02d}.{ext}"
        out_path.write_text(chunk, encoding="utf-8")
        parts.append(out_path)

    return parts
