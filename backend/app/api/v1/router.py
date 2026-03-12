from fastapi import APIRouter

from .routes import transcription, chat, ollama_routes

api_router = APIRouter()
api_router.include_router(transcription.router, prefix="/transcribe", tags=["transcription"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(ollama_routes.router, prefix="/ollama", tags=["ollama"])
