from __future__ import annotations

import asyncio
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from ....core.config import get_settings
from ....services.media import extract_audio_segments
from ....services.transcription import transcribe_files
from ....services.text import concat_and_chunk_with_header

router = APIRouter()
settings = get_settings()

# Máx. 2 transcripciones simultáneas (Whisper es CPU-bound)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="whisper")


@router.post(
    "/",
    summary="Transcribe un fichero de audio/video",
    description="Responde con SSE: eventos 'progress' y un evento final 'result' o 'error'.",
)
async def transcribe(
    file: UploadFile = File(...),
    whisper_model: str = Form("base"),
    language: str = Form(""),
    segment_seconds: int = Form(300),
    max_chars: int = Form(20000),
    output_format: str = Form("txt"),
    header_template: str = Form("<<TRANSCRIPCION>>\n"),
):
    content = await file.read()
    filename = file.filename or "input"

    async def event_stream():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict] = asyncio.Queue()
        lang = language.strip() or None

        def run() -> None:
            try:
                with tempfile.TemporaryDirectory(prefix="ft_") as tmpdir:
                    work = Path(tmpdir)
                    mp3_dir = work / "mp3"
                    txt_dir = work / "txt"
                    mp3_dir.mkdir()
                    txt_dir.mkdir()

                    input_path = work / filename
                    input_path.write_bytes(content)

                    _emit(loop, queue, "progress", step="extracting_audio", pct=10)
                    mp3_list = extract_audio_segments(
                        input_path, mp3_dir, segment_seconds
                    )

                    _emit(loop, queue, "progress", step="loading_model", pct=25)
                    # get_model() cachea el modelo; primer uso tarda más

                    _emit(loop, queue, "progress", step="transcribing", pct=40)
                    txt_list = transcribe_files(
                        mp3_list, txt_dir, whisper_model, lang
                    )

                    _emit(loop, queue, "progress", step="compiling", pct=85)
                    out_dir = Path(settings.output_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)

                    tmpl = header_template.replace("\\n", "\n")
                    parts = concat_and_chunk_with_header(
                        txt_files=txt_list,
                        out_dir=out_dir,
                        max_chars=max_chars,
                        header_template=tmpl,
                        language=lang,
                        source_name=filename,
                        output_ext=output_format,
                    )

                    result_parts = [
                        {"filename": p.name, "content": p.read_text(encoding="utf-8")}
                        for p in parts
                    ]
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {"type": "result", "parts": result_parts},
                    )
            except Exception as exc:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "error", "message": str(exc)},
                )

        future = loop.run_in_executor(_executor, run)
        yield _sse({"type": "progress", "step": "queued", "pct": 0})

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield _sse(event)
                if event["type"] in ("result", "error"):
                    break
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # keep-alive

        await future

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _emit(
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
    type_: str,
    **kwargs: object,
) -> None:
    loop.call_soon_threadsafe(queue.put_nowait, {"type": type_, **kwargs})
