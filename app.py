import sys
import threading
import queue
import shutil
from pathlib import Path
from typing import List
import flet as ft

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flow_transcriber.config import settings
from flow_transcriber.media.mkv_to_mp3 import extract_audio_segments
from flow_transcriber.transcribe.whisper_transcriber import WhisperTranscriber
from flow_transcriber.text.splitter import concat_and_chunk_with_header


def clean_dir(p: Path):
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def ensure_clean_work(mp3_dir: Path, txt_dir: Path):
    clean_dir(mp3_dir.parent if mp3_dir.name == "mp3" else mp3_dir)
    clean_dir(txt_dir.parent if txt_dir.name == "txt" else txt_dir)
    mp3_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)


def main(page: ft.Page):
    page.title = "Flow Transcriber (Flet)"
    page.window_width = 1200
    page.window_height = 800
    page.scroll = ft.ScrollMode.ALWAYS
    page.theme_mode = ft.ThemeMode.DARK

    selected_files: List[Path] = []

    file_picker = ft.FilePicker()
    dir_picker_out = ft.FilePicker()
    page.overlay.extend([file_picker, dir_picker_out])

    whisper_model_dd = ft.Dropdown(
        label="Modelo Whisper",
        options=[ft.dropdown.Option(x) for x in ["tiny", "base", "small", "medium", "large"]],
        value=settings.whisper_model,
        expand=True,
    )
    language_tf = ft.TextField(label="Idioma (ISO, vacío = autodetect)", value=(settings.language or "es"), expand=True)
    segment_secs_tf = ft.TextField(label="Segmento (seg.)", value=str(settings.segment_seconds or 300), expand=True)
    max_chars_tf = ft.TextField(label="Máx. caracteres por TXT", value=str(settings.max_chars or 20000), expand=True)
    header_template_ta = ft.TextField(
        label="Encabezado / Prompt",
        value=settings.header_template,
        multiline=True,
        min_lines=6,
        max_lines=10,
        expand=True,
    )

    input_file_tf = ft.TextField(label="Fichero .mkv", expand=True, read_only=True)
    output_dir_tf = ft.TextField(label="Directorio de salida final", value=str(Path(settings.output_dir)), expand=True)
    work_mp3_tf = ft.TextField(label="Work MP3", value=str(Path(settings.work_mp3_dir)), expand=True)
    work_txt_tf = ft.TextField(label="Work TXT", value=str(Path(settings.work_txt_dir)), expand=True)

    files_lv = ft.ListView(expand=True, spacing=6, height=240, auto_scroll=True)
    log_area = ft.TextField(
        value="", multiline=True, min_lines=8, max_lines=14, expand=True,
        read_only=True, border=ft.InputBorder.OUTLINE, label="Log"
    )
    progress = ft.ProgressBar(width=400, value=0)

    log_queue: "queue.Queue[str]" = queue.Queue()
    progress_queue: "queue.Queue[float]" = queue.Queue()
    done_flag = threading.Event()

    def refresh_loop():
        while not done_flag.is_set():
            updated = False
            while not log_queue.empty():
                msg = log_queue.get_nowait()
                log_area.value = (log_area.value or "") + msg + "\n"
                updated = True
            while not progress_queue.empty():
                v = progress_queue.get_nowait()
                progress.value = v
                updated = True
            if updated:
                try:
                    page.update()
                except Exception:
                    pass
            threading.Event().wait(0.4)

    def on_pick_file(e: ft.FilePickerResultEvent):
        selected_files.clear()
        files_lv.controls.clear()
        if e.files and len(e.files) > 0:
            path = e.files[0].path
            input_file_tf.value = path
            p = Path(path)
            if p.exists():
                selected_files.append(p)
                files_lv.controls.append(ft.Text(str(p)))
            else:
                files_lv.controls.append(ft.Text("Ruta inválida o inexistente"))
        else:
            input_file_tf.value = ""
            files_lv.controls.append(ft.Text("No se seleccionó fichero"))
        page.update()

    def on_pick_output_dir(e: ft.FilePickerResultEvent):
        if e.path:
            output_dir_tf.value = e.path
            page.update()

    file_picker.on_result = on_pick_file
    dir_picker_out.on_result = on_pick_output_dir

    def choose_file_click(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["mkv"])

    def choose_out_dir_click(e):
        dir_picker_out.get_directory_path()

    def run_processing():
        try:
            model_name = whisper_model_dd.value or "base"
            lang = (language_tf.value or "").strip() or None
            seg = int(segment_secs_tf.value or "300")
            max_chars = int(max_chars_tf.value or "20000")
            header_tpl = header_template_ta.value or "<<TRANSCRIPCION>>\n"

            out_dir = Path(output_dir_tf.value).resolve()
            mp3_dir = Path(work_mp3_tf.value).resolve()
            txt_dir = Path(work_txt_tf.value).resolve()

            ensure_clean_work(mp3_dir, txt_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            log_queue.put(f"Salida: {out_dir}")
            log_queue.put("Cargando Whisper")
            transcriber = WhisperTranscriber(model_name=model_name, language=lang)

            total = len(selected_files)
            done = 0

            for mkv in list(selected_files):
                try:
                    log_queue.put(f"Procesando: {mkv.name}")
                    mp3_list = extract_audio_segments(mkv, mp3_dir, seg)
                    log_queue.put(f"MP3: {len(mp3_list)}")
                    txt_list = transcriber.transcribe_files(mp3_list, txt_dir)
                    log_queue.put(f"TXT: {len(txt_list)}")
                    parts = concat_and_chunk_with_header(
                        txt_files=txt_list,
                        out_dir=out_dir,
                        max_chars=max_chars,
                        header_template=header_tpl,
                        language=(lang or None),
                        source_name=mkv.name,
                    )
                    for p in parts:
                        log_queue.put(str(p.resolve()))
                except Exception as ex:
                    log_queue.put(f"Error: {ex}")
                    raise
                done += 1
                progress_queue.put(done / max(total, 1))

            log_queue.put("Finalizado")
        except Exception as ex:
            log_queue.put(f"Fallo general: {ex}")
        finally:
            try:
                p = Path(work_mp3_tf.value).resolve()
                clean_dir(p.parent if p.name == "mp3" else p)
            except Exception:
                pass
            try:
                p = Path(work_txt_tf.value).resolve()
                clean_dir(p.parent if p.name == "txt" else p)
            except Exception:
                pass
            done_flag.set()

    def process_click(e):
        files_lv.controls.clear()
        selected_files.clear()
        if input_file_tf.value.strip():
            p = Path(input_file_tf.value.strip())
            if p.exists() and p.is_file():
                selected_files.append(p)
                files_lv.controls.append(ft.Text(str(p)))
            else:
                files_lv.controls.append(ft.Text("Ruta de fichero inválida o inexistente"))
        else:
            files_lv.controls.append(ft.Text("No hay fichero seleccionado"))
        page.update()
        if not selected_files:
            log_area.value = (log_area.value or "") + "Sin archivos para procesar\n"
            page.update()
            return
        progress.value = 0
        log_area.value = ""
        page.update()

        try:
            p = Path(work_mp3_tf.value).resolve()
            clean_dir(p.parent if p.name == "mp3" else p)
            p = Path(work_txt_tf.value).resolve()
            clean_dir(p.parent if p.name == "txt" else p)
        except Exception:
            pass

        done_flag.clear()
        threading.Thread(target=refresh_loop, daemon=True).start()
        threading.Thread(target=run_processing, daemon=True).start()

    left_panel = ft.Column([
        ft.Text("Carga de fichero", weight=ft.FontWeight.BOLD),
        ft.Row([
            input_file_tf,
            ft.ElevatedButton("Elegir fichero", icon=ft.Icon(name="insert_drive_file"), on_click=choose_file_click)
        ], spacing=8),
        ft.Text("Archivos seleccionados", size=12),
        ft.Container(content=files_lv, height=240),
    ], spacing=10, expand=True)

    right_panel = ft.Column([
        ft.Text("Procesamiento", weight=ft.FontWeight.BOLD),
        ft.Row([ft.ElevatedButton("Procesar", on_click=process_click), progress], spacing=12),
        ft.Row([
            output_dir_tf,
            ft.ElevatedButton("Elegir salida", icon=ft.Icon(name="folder"), on_click=choose_out_dir_click)
        ], spacing=8),
        ft.Container(content=log_area, height=200),
    ], spacing=10, expand=True)

    top_group = ft.Row([left_panel, right_panel], spacing=16)

    config_group = ft.Column([
        ft.Text("Configuración", weight=ft.FontWeight.BOLD),
        ft.Row([whisper_model_dd, language_tf, segment_secs_tf, max_chars_tf], spacing=12),
        header_template_ta,
        ft.Row([work_mp3_tf, work_txt_tf], spacing=8),
    ], spacing=10)

    page.add(top_group, ft.Divider(), config_group)


if __name__ == "__main__":
    ft.app(target=main)
