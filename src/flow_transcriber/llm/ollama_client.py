from __future__ import annotations

from typing import Iterator, List

import ollama


class OllamaClient:
    """Thin wrapper around the Ollama Python SDK with streaming support."""

    def __init__(self, model: str, host: str = "http://localhost:11434") -> None:
        self._model = model
        self._client = ollama.Client(host=host)

    def stream_chat(
        self,
        messages: List[dict],
        system: str = "",
    ) -> Iterator[str]:
        """Stream tokens from OLLAMA for the given conversation.

        Args:
            messages: List of {"role": "user"|"assistant", "content": ...}
            system:   Optional system prompt (prepended automatically).
        """
        all_messages: list[dict] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        stream = self._client.chat(
            model=self._model,
            messages=all_messages,
            stream=True,
        )
        for chunk in stream:
            token = chunk["message"]["content"]
            if token:
                yield token

    def available_models(self) -> list[str]:
        """Return list of model names installed locally in the OLLAMA instance.
        Returns an empty list on connection failure."""
        try:
            result = self._client.list()
            # result is a ListResponse with a .models attribute (list of Model objects)
            models = getattr(result, "models", None) or result.get("models", [])
            return sorted(str(getattr(m, "model", m.get("model", ""))) for m in models)
        except Exception:
            return []

    def is_connected(self) -> bool:
        """Return True if the OLLAMA instance is reachable."""
        try:
            self._client.list()
            return True
        except Exception:
            return False
