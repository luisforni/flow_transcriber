from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
import whisper

def _normalize_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    return lang.split("_")[0].split("-")[0].lower()

class WhisperTranscriber:
    def __init__(self, model_name: str = "base", language: str | None = None) -> None:
        self.model = whisper.load_model(model_name)
        self.language = _normalize_lang(language)

    def transcribe_files(self, audio_files: Iterable[Path], out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        created: List[Path] = []
        for p in audio_files:
            if not p.exists():
                continue
            kwargs = {}
            if self.language:
                kwargs["language"] = self.language
            result = self.model.transcribe(str(p), **kwargs)
            text = (result.get("text") or "").strip()
            out_path = out_dir / f"{p.stem}.txt"
            out_path.write_text(text, encoding="utf-8")
            created.append(out_path)
        return created
