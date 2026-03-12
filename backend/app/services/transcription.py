from __future__ import annotations

from pathlib import Path
from typing import Any

import whisper

# Cache de modelos en memoria: evita re-cargar Whisper en cada petición
_model_cache: dict[str, Any] = {}


def get_model(model_name: str) -> Any:
    if model_name not in _model_cache:
        _model_cache[model_name] = whisper.load_model(model_name)
    return _model_cache[model_name]


def _normalize_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    return lang.split("_")[0].split("-")[0].lower()


def transcribe_files(
    audio_files: list[Path],
    out_dir: Path,
    model_name: str,
    language: str | None,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    model = get_model(model_name)
    lang = _normalize_lang(language)

    created: list[Path] = []
    for p in audio_files:
        if not p.exists():
            continue
        kwargs: dict[str, Any] = {}
        if lang:
            kwargs["language"] = lang
        result = model.transcribe(str(p), **kwargs)
        text = (result.get("text") or "").strip()
        out_path = out_dir / f"{p.stem}.txt"
        out_path.write_text(text, encoding="utf-8")
        created.append(out_path)

    return created
