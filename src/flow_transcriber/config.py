from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    # ── Whisper ──────────────────────────────────────────────────────────────
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    language: str | None = os.getenv("LANGUAGE") or None
    segment_seconds: int = int(os.getenv("SEGMENT_DURATION", "300"))
    max_chars: int = int(os.getenv("MAX_CHARS", "20000"))
    header_template: str = os.getenv("HEADER_PROMPT_TEMPLATE", "<<TRANSCRIPCION>>\n").replace("\\n", "\n")
    output_dir: str = os.getenv("OUTPUT_DIR", "out")
    work_mp3_dir: str = os.getenv("WORK_MP3_DIR", ".work/mp3")
    work_txt_dir: str = os.getenv("WORK_TXT_DIR", ".work/txt")

    # ── OLLAMA ───────────────────────────────────────────────────────────────
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")
    ollama_system_prompt: str = os.getenv(
        "OLLAMA_SYSTEM_PROMPT",
        "Eres un asistente experto en análisis de transcripciones de audio. "
        "Responde en español de forma clara y concisa. "
        "Cuando el usuario te proporcione una transcripción, analízala y responde sus preguntas sobre ella.",
    )

settings = Settings()
