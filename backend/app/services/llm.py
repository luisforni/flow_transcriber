from __future__ import annotations

from typing import AsyncIterator

import ollama as _ollama


class OllamaService:
    """Async wrapper alrededor del SDK de Ollama."""

    async def stream_chat(
        self,
        messages: list[dict],
        *,
        model: str,
        host: str,
        system: str = "",
    ) -> AsyncIterator[str]:
        client = _ollama.AsyncClient(host=host)
        all_messages: list[dict] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        async for chunk in await client.chat(
            model=model, messages=all_messages, stream=True
        ):
            token = chunk["message"]["content"]
            if token:
                yield token

    async def available_models(self, host: str) -> list[str]:
        try:
            client = _ollama.AsyncClient(host=host)
            result = await client.list()
            models = getattr(result, "models", None) or result.get("models", [])
            return sorted(
                str(getattr(m, "model", m.get("model", ""))) for m in models
            )
        except Exception:
            return []

    async def is_connected(self, host: str) -> bool:
        try:
            client = _ollama.AsyncClient(host=host)
            await client.list()
            return True
        except Exception:
            return False


ollama_service = OllamaService()
