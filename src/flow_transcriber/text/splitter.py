from __future__ import annotations
from typing import Iterable, List
from pathlib import Path
from .header import build_header

def concat_and_chunk_with_header(
    txt_files: Iterable[Path],
    out_dir: Path,
    max_chars: int,
    header_template: str,
    language: str | None,
    source_name: str,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(list(txt_files))
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
    parts: List[Path] = []
    start = 0
    part_no = 1
    while start < len(big_text):
        chunk = big_text[start:start + max_chars]
        out_path = out_dir / f"{Path(source_name).stem}_final_part{part_no:02d}.txt"
        out_path.write_text(chunk, encoding="utf-8")
        parts.append(out_path)
        start += max_chars
        part_no += 1
    return parts
