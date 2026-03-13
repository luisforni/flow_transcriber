"use client";

import { useState, useRef } from "react";
import { transcribeStream, fetchModels } from "@/lib/api";
import type { Part, TranscribeEvent } from "@/lib/api";

const WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"];
const STEP_LABELS: Record<string, string> = {
  queued: "En cola…",
  extracting_audio: "Extrayendo audio…",
  loading_model: "Cargando modelo Whisper…",
  transcribing: "Transcribiendo… (puede tardar)",
  compiling: "Compilando resultado…",
};

type Props = {
  parts: Part[];
  ollamaHost: string;
  onResult: (parts: Part[], autoPrompt: string) => void;
};

type TranscribeState =
  | { status: "idle" }
  | { status: "progress"; step: string; pct: number }
  | { status: "error"; message: string };

export default function TranscribePanel({ parts, ollamaHost, onResult }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [state, setState] = useState<TranscribeState>({ status: "idle" });
  const [expandedPart, setExpandedPart] = useState<string | null>(null);

  // Whisper settings
  const [whisperModel, setWhisperModel] = useState("base");
  const [language, setLanguage] = useState("es");
  const [segmentSeconds, setSegmentSeconds] = useState(300);
  const [maxChars, setMaxChars] = useState(20000);
  const [outputFormat, setOutputFormat] = useState("txt");

  const inputRef = useRef<HTMLInputElement>(null);
  const hasParts = parts.length > 0;

  async function handleTranscribe() {
    if (!file) return;
    setState({ status: "progress", step: "queued", pct: 0 });

    const formData = new FormData();
    formData.append("file", file);
    formData.append("whisper_model", whisperModel);
    formData.append("language", language);
    formData.append("segment_seconds", String(segmentSeconds));
    formData.append("max_chars", String(maxChars));
    formData.append("output_format", outputFormat);

    try {
      for await (const event of transcribeStream(formData)) {
        if (event.type === "progress") {
          setState({ status: "progress", step: event.step, pct: event.pct });
        } else if (event.type === "result") {
          setState({ status: "idle" });
          onResult(event.parts, AUTO_PROMPT);
        } else if (event.type === "error") {
          setState({ status: "error", message: event.message });
        }
      }
    } catch (err) {
      setState({ status: "error", message: String(err) });
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
      <h2 className="text-lg font-semibold">🎤 Transcripción</h2>

      {/* ── Zona de upload ── */}
      {!hasParts && (
        <>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
              ${dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-blue-300 hover:bg-gray-50"}`}
          >
            <p className="text-3xl mb-2">📂</p>
            <p className="text-sm text-gray-500">
              {file ? file.name : "Arrastra un fichero o haz clic para seleccionar"}
            </p>
            {file && (
              <p className="text-xs text-gray-400 mt-1">
                {(file.size / 1_048_576).toFixed(1)} MB
              </p>
            )}
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept=".mkv,.mp4,.avi,.mov,.webm,.flv,.mp3,.wav,.m4a,.ogg,.flac,.aac"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {/* Ajustes compactos */}
          <details className="text-sm">
            <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
              ⚙️ Ajustes Whisper
            </summary>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs text-gray-500">Modelo</span>
                <select
                  value={whisperModel}
                  onChange={(e) => setWhisperModel(e.target.value)}
                  className="w-full border rounded-lg px-2 py-1.5 text-sm"
                >
                  {WHISPER_MODELS.map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs text-gray-500">Idioma (ISO)</span>
                <input
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  placeholder="es, en, fr…"
                  className="w-full border rounded-lg px-2 py-1.5 text-sm"
                />
              </label>
              <label className="space-y-1">
                <span className="text-xs text-gray-500">Segmento (seg.)</span>
                <input
                  type="number"
                  value={segmentSeconds}
                  onChange={(e) => setSegmentSeconds(Number(e.target.value))}
                  className="w-full border rounded-lg px-2 py-1.5 text-sm"
                />
              </label>
              <label className="space-y-1">
                <span className="text-xs text-gray-500">Máx. chars/fichero</span>
                <input
                  type="number"
                  value={maxChars}
                  onChange={(e) => setMaxChars(Number(e.target.value))}
                  className="w-full border rounded-lg px-2 py-1.5 text-sm"
                />
              </label>
              <label className="space-y-1 col-span-2">
                <span className="text-xs text-gray-500">Formato de salida</span>
                <div className="flex gap-3">
                  {["txt", "md"].map((f) => (
                    <label key={f} className="flex items-center gap-1 text-sm">
                      <input
                        type="radio"
                        name="fmt"
                        value={f}
                        checked={outputFormat === f}
                        onChange={() => setOutputFormat(f)}
                      />
                      {f}
                    </label>
                  ))}
                </div>
              </label>
            </div>
          </details>

          {/* Botón transcribir */}
          <button
            disabled={!file || state.status === "progress"}
            onClick={handleTranscribe}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white
                       font-semibold py-2.5 rounded-xl transition-colors"
          >
            {state.status === "progress" ? "Transcribiendo…" : "▶️ Transcribir"}
          </button>

          {/* Barra de progreso */}
          {state.status === "progress" && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-500">
                <span>{STEP_LABELS[state.step] ?? state.step}</span>
                <span>{state.pct}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${state.pct}%` }}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {state.status === "error" && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3">
              ❌ {state.message}
            </div>
          )}
        </>
      )}

      {/* ── Resultados ── */}
      {hasParts && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">
              ✅ {parts.length} parte(s) generada(s)
            </span>
            <button
              onClick={() => onResult([], "")}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              🗑️ Nueva transcripción
            </button>
          </div>

          {parts.map((part) => (
            <div key={part.filename} className="border rounded-xl overflow-hidden">
              <button
                onClick={() =>
                  setExpandedPart(
                    expandedPart === part.filename ? null : part.filename
                  )
                }
                className="w-full flex justify-between items-center px-4 py-2.5 bg-gray-50 text-sm font-medium hover:bg-gray-100 transition-colors"
              >
                <span>📄 {part.filename}</span>
                <span className="text-gray-400">
                  {expandedPart === part.filename ? "▲" : "▼"}
                </span>
              </button>

              {expandedPart === part.filename && (
                <div className="p-3 space-y-2">
                  <textarea
                    readOnly
                    value={part.content}
                    rows={8}
                    className="w-full text-xs font-mono border rounded-lg p-2 resize-y thin-scroll"
                  />
                  <a
                    href={`data:text/plain;charset=utf-8,${encodeURIComponent(part.content)}`}
                    download={part.filename}
                    className="inline-block text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    ⬇️ Descargar {part.filename}
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const AUTO_PROMPT =
  "Acabo de transcribir un audio. Analiza el contenido, " +
  "haz un resumen claro y destaca los puntos más importantes.";
