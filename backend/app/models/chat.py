from __future__ import annotations

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    transcription: str = ""
    model: str = "llama3"
    host: str = "http://localhost:11434"
    system_prompt: str = ""
