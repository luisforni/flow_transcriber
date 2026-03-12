from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ....models.chat import ChatRequest
from ....services.llm import ollama_service

router = APIRouter()


@router.post(
    "/stream",
    summary="Streaming de chat con Ollama (SSE)",
    description="Envía mensajes y recibe tokens en tiempo real vía Server-Sent Events.",
)
async def chat_stream(req: ChatRequest):
    system = req.system_prompt
    if req.transcription:
        system += "\n\n---\nCONTEXTO — transcripción del audio:\n" + req.transcription

    async def event_stream():
        try:
            async for token in ollama_service.stream_chat(
                messages=[m.model_dump() for m in req.messages],
                model=req.model,
                host=req.host,
                system=system,
            ):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
