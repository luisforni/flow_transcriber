from __future__ import annotations

from fastapi import APIRouter, Query

from ....core.config import get_settings
from ....services.llm import ollama_service

router = APIRouter()
settings = get_settings()


@router.get("/models", summary="Lista modelos Ollama instalados")
async def list_models(
    host: str = Query(default=None, description="URL del host Ollama")
):
    h = host or settings.ollama_host
    models = await ollama_service.available_models(host=h)
    return {"models": models, "connected": bool(models)}


@router.get("/health", summary="Verifica conectividad con Ollama")
async def ollama_health(
    host: str = Query(default=None, description="URL del host Ollama")
):
    h = host or settings.ollama_host
    connected = await ollama_service.is_connected(host=h)
    return {"connected": connected, "host": h}
