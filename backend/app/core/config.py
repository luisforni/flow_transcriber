from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Busca .env en el directorio del backend O en el padre (monorepo root)
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        extra="ignore",
    )

    # Whisper
    whisper_model: str = "base"
    language: Optional[str] = None
    segment_seconds: int = 300
    max_chars: int = 20000
    header_template: str = "<<TRANSCRIPCION>>\n"
    output_dir: str = "out"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_system_prompt: str = (
        "Eres un asistente experto en análisis de transcripciones de audio. "
        "Responde en español de forma clara y concisa. "
        "Cuando el usuario te proporcione una transcripción, analízala y responde "
        "sus preguntas sobre ella."
    )

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8501",
    ]

    @field_validator("language", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        return v or None

    @field_validator("header_template", mode="after")
    @classmethod
    def unescape_newlines(cls, v: str) -> str:
        return v.replace("\\n", "\n")


@lru_cache
def get_settings() -> Settings:
    return Settings()
