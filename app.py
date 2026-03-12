import sys
import os
import shutil
import tempfile
from pathlib import Path

import streamlit as st

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flow_transcriber.config import settings
from flow_transcriber.media.extractor import extract_audio_segments, SUPPORTED_EXTENSIONS
from flow_transcriber.transcribe.whisper_transcriber import WhisperTranscriber
from flow_transcriber.text.splitter import concat_and_chunk_with_header
from flow_transcriber.llm.ollama_client import OllamaClient


def clean_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Flow Transcriber",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Oculta el menú de hamburguesa y footer de Streamlit */
    #MainMenu, footer { visibility: hidden; }

    /* Encabezado principal */
    .ft-title { font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 0; }
    .ft-sub   { color: #888; font-size: 0.9rem; margin-top: 2px; }

    /* Tarjetas de estado */
    .ft-card {
        background: #f8f9fb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
    }

    /* Chat messages más redondeados */
    [data-testid="stChatMessage"] { border-radius: 14px; }

    /* Sidebar compacto */
    [data-testid="stSidebar"] { min-width: 260px; max-width: 290px; }
    [data-testid="stSidebar"] h3 { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {
    "chat_messages": [],
    "transcription_text": "",
    "transcription_parts": [],   # list of (filename, content) tuples
    "auto_message": "",          # auto-sent to OLLAMA after transcription
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎙️ Flow Transcriber")
    st.divider()

    # OLLAMA (primero porque es lo más importante)
    st.markdown("**🤖 OLLAMA**")
    ollama_host = st.text_input("Host", value=settings.ollama_host, label_visibility="collapsed",
                                 placeholder="http://localhost:11434")

    _client = OllamaClient(model="", host=ollama_host)
    _available = _client.available_models()

    if _available:
        _idx = _available.index(settings.ollama_model) if settings.ollama_model in _available else 0
        ollama_model_sel = st.selectbox(
            "Modelo IA",
            options=_available,
            index=_idx,
            help="Modelos instalados localmente en OLLAMA. Instala más con: ollama pull <nombre>",
        )
        st.caption(f"✅ Conectado · {len(_available)} modelo(s) instalado(s)")
    else:
        st.warning("⚠️ OLLAMA sin conexión — ejecuta `ollama serve`")
        ollama_model_sel = st.text_input("Modelo (manual)", value=settings.ollama_model,
                                          placeholder="llama3, mistral, phi3…")

    st.divider()

    # Whisper
    st.markdown("**🎤 Whisper**")
    whisper_model = st.selectbox(
        "Modelo transcripción",
        ["tiny", "base", "small", "medium", "large"],
        index=["tiny", "base", "small", "medium", "large"].index(settings.whisper_model),
    )
    language = st.text_input("Idioma (ISO)", value=settings.language or "es",
                              placeholder="es, en, fr…")

    st.divider()

    # Avanzado colapsado
    with st.expander("⚙️ Ajustes avanzados"):
        segment_secs  = st.number_input("Segmento (seg.)", 30, 3600, settings.segment_seconds or 300, 30)
        max_chars     = st.number_input("Máx. chars/fichero", 1000, 200000, settings.max_chars or 20000, 1000)
        output_format = st.radio("Formato", ["txt", "md"], horizontal=True)
        output_dir    = st.text_input("Dir. salida", value=str(Path(settings.output_dir).resolve()))
        header_tmpl   = st.text_area("Encabezado fichero", value=settings.header_template, height=70)
        ollama_system = st.text_area("System prompt IA", value=settings.ollama_system_prompt, height=110)

    st.divider()
    if st.button("🗑️ Nueva sesión", use_container_width=True):
        st.session_state.chat_messages    = []
        st.session_state.transcription_text  = ""
        st.session_state.transcription_parts = []
        st.session_state.auto_message     = ""
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<p class="ft-title">🎙️ Flow Transcriber</p>', unsafe_allow_html=True)
st.markdown('<p class="ft-sub">Transcribe audio · Analiza con IA local (OLLAMA)</p>', unsafe_allow_html=True)
st.write("")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — SUBIDA Y TRANSCRIPCIÓN
# ═══════════════════════════════════════════════════════════════════════════════
# Sólo se muestra si aún no hay transcripción
if not st.session_state.transcription_text:
    ext_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    uploaded = st.file_uploader(
        f"Arrastra o selecciona un fichero de audio/video  ·  {ext_list}",
        type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
        label_visibility="visible",
    )

    col_info, col_btn = st.columns([4, 1])
    if uploaded:
        col_info.info(f"📄 **{uploaded.name}**  ·  {uploaded.size / 1_048_576:.1f} MB")
    col_btn.write("")  # spacing
    run = col_btn.button("▶️ Transcribir", type="primary", disabled=uploaded is None, use_container_width=True)

    if run and uploaded:
        out_dir   = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        work_root = Path(tempfile.mkdtemp(prefix="ft_"))
        mp3_dir   = work_root / "mp3"
        txt_dir   = work_root / "txt"
        mp3_dir.mkdir(); txt_dir.mkdir()

        tmp_input = work_root / f"input{Path(uploaded.name).suffix}"
        tmp_input.write_bytes(uploaded.read())

        status_box = st.empty()
        bar = st.progress(0, text="Iniciando…")

        try:
            bar.progress(0.05, text="Extrayendo audio…")
            mp3_list = extract_audio_segments(tmp_input, mp3_dir, int(segment_secs))
            bar.progress(0.30, text=f"{len(mp3_list)} segmento(s) extraído(s)")

            bar.progress(0.40, text="Cargando modelo Whisper…")
            lang = language.strip() or None
            transcriber = WhisperTranscriber(model_name=whisper_model, language=lang)

            bar.progress(0.50, text="Transcribiendo… (puede tardar)")
            txt_list = transcriber.transcribe_files(mp3_list, txt_dir)
            bar.progress(0.85, text="Compilando fichero…")

            parts = concat_and_chunk_with_header(
                txt_files=txt_list,
                out_dir=out_dir,
                max_chars=int(max_chars),
                header_template=header_tmpl,
                language=lang,
                source_name=uploaded.name,
                output_ext=output_format,
            )
            bar.progress(1.0, text="✅ Transcripción completada")

            # Guardar en session state
            st.session_state.transcription_text  = "\n\n".join(
                p.read_text(encoding="utf-8") for p in parts
            )
            st.session_state.transcription_parts = [
                (p.name, p.read_text(encoding="utf-8")) for p in parts
            ]
            # Desencadenar análisis automático en OLLAMA
            st.session_state.auto_message = (
                "Acabo de transcribir un audio. Analiza el contenido, "
                "haz un resumen claro y destaca los puntos más importantes."
            )

        except Exception as ex:
            status_box.error(f"❌ Error durante la transcripción: {ex}")
            st.exception(ex)
        finally:
            clean_dir(work_root)

        st.rerun()

else:
    # ── Resultado de transcripción (compacto, colapsado) ─────────────────────
    n_parts = len(st.session_state.transcription_parts)
    with st.expander(f"📄 Transcripción lista — {n_parts} parte(s)  ·  click para ver / descargar"):
        for fname, content in st.session_state.transcription_parts:
            st.caption(f"**{fname}**")
            st.text_area(fname, content, height=220, key=f"view_{fname}", label_visibility="collapsed")
            st.download_button(
                f"⬇️ Descargar {fname}",
                data=content.encode("utf-8"),
                file_name=fname,
                mime="text/plain",
                key=f"dl_{fname}",
            )
        st.write("")

    # ── Re-analizar con otro modelo ───────────────────────────────────────────
    col_rerun, col_info = st.columns([1, 3])
    if col_rerun.button("🔄 Re-analizar con IA", use_container_width=True,
                         help="Limpia el chat y vuelve a analizar la transcripción con el modelo seleccionado en la barra lateral"):
        st.session_state.chat_messages = []
        st.session_state.auto_message = (
            "Acabo de transcribir un audio. Analiza el contenido, "
            "haz un resumen claro y destaca los puntos más importantes."
        )
        st.rerun()
    col_info.caption(f"Modelo activo: **{ollama_model_sel}** · Cambia el modelo en la barra lateral antes de re-analizar.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — CHAT CON OLLAMA
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.transcription_text and not st.session_state.chat_messages:
    st.markdown(
        "<div style='text-align:center;color:#aaa;padding:3rem 0'>"
        "🤖 Transcribe un fichero de audio para comenzar el análisis con IA,<br>"
        "o escribe directamente en el chat para una conversación libre."
        "</div>",
        unsafe_allow_html=True,
    )

# Mostrar historial de mensajes
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Determinar prompt: auto (post-transcripción) o manual ────────────────────
auto_msg = st.session_state.auto_message
if auto_msg:
    st.session_state.auto_message = ""   # limpiar antes de renderizar

user_input = st.chat_input(
    "Pregunta sobre la transcripción o inicia una conversación…"
    if st.session_state.transcription_text
    else "Chat libre con OLLAMA…"
)

current_prompt = auto_msg or user_input

if current_prompt:
    # Si es auto_message mostramos un mensaje de usuario más amigable
    display_prompt = (
        "📋 *Analizando la transcripción automáticamente…*"
        if auto_msg else current_prompt
    )

    st.session_state.chat_messages.append({"role": "user", "content": display_prompt})
    with st.chat_message("user"):
        st.markdown(display_prompt)

    # System prompt: inyectar transcripción si existe
    ctx = st.session_state.transcription_text.strip()
    system_ctx = (
        (ollama_system if "ollama_system" in dir() else settings.ollama_system_prompt)
        + ("\n\n---\nCONTEXTO — transcripción del audio:\n" + ctx if ctx else "")
    )

    ollama_client = OllamaClient(
        model=ollama_model_sel,
        host=ollama_host,
    )
    with st.chat_message("assistant"):
        try:
            response = st.write_stream(
                ollama_client.stream_chat(
                    messages=st.session_state.chat_messages,
                    system=system_ctx,
                )
            )
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
        except Exception as ex:
            st.error(
                f"❌ No se pudo conectar con OLLAMA en `{ollama_host}`.\n\n"
                f"**Detalle:** `{ex}`\n\n"
                "Verifica que el servicio esté activo: `ollama serve`"
            )


if __name__ == "__main__":
    import subprocess
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", __file__,
        "--server.port", os.getenv("PORT", "8501"),
        "--server.address", os.getenv("HOST", "127.0.0.1"),
    ])

