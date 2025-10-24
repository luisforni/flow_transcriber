WHISPER_MODEL=base

LANGUAGE=es

SEGMENT_DURATION=300

MAX_CHARS=20000

HEADER_PROMPT_TEMPLATE=<<INSTRUCCIONES PARA CHATGPT>>\nEres un asistente que va a resumir una reunión transcrita con Whisper.\n- Ten en cuenta que puede haber errores de transcripción, cortes o modismos.\n- Objetivo: crear un resumen ejecutivo con acuerdos, decisiones, responsables y próximos pasos.\n- Si hay dudas, enuméralas como 'Riesgos/Incógnitas'.\nMetadatos: archivo={file_name}, origen={source_name}, idioma={language}, fecha={now_iso}, parte={segment_index}/{segment_count}.\n== TRANSCRIPCIÓN ==\n

OUTPUT_DIR=out

WORK_MP3_DIR=.work/mp3

WORK_TXT_DIR=.work/txt
