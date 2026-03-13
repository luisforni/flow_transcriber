"use client";

import { useEffect, useRef, useState } from "react";
import { chatStream, fetchModels } from "@/lib/api";
import type { ChatMessage } from "@/lib/api";
import ReactMarkdown from "react-markdown";

type Props = {
  transcription: string;
  messages: ChatMessage[];
  onMessages: (msgs: ChatMessage[]) => void;
  autoPrompt?: string;
  onAutoPromptConsumed?: () => void;
};

export default function ChatPanel({
  transcription,
  messages,
  onMessages,
  autoPrompt,
  onAutoPromptConsumed,
}: Props) {
  const [host, setHost] = useState("http://localhost:11434");
  const [model, setModel] = useState("");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [systemPrompt, setSystemPrompt] = useState(
    "Eres un asistente experto en análisis de transcripciones de audio. " +
      "Responde en español de forma clara y concisa."
  );
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Cargar modelos al montar o cuando cambia el host
  useEffect(() => {
    fetchModels(host).then((models) => {
      setAvailableModels(models);
      // Asignar el primer modelo disponible si no hay uno seleccionado
      if (models.length > 0) {
        if (!model || !models.includes(model)) {
          setModel(models[0]);
        }
      }
    });
  }, [host]);

  // Scroll automático al final
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Ejecutar prompt automático (post-transcripción)
  useEffect(() => {
    if (autoPrompt && !streaming) {
      onAutoPromptConsumed?.();
      sendMessage(autoPrompt, true);
    }
  }, [autoPrompt]);

  async function sendMessage(text: string, isAuto = false) {
    if (!text.trim() || streaming) return;
    setError("");

    const userMsg: ChatMessage = {
      role: "user",
      content: isAuto ? "📋 *Analizando la transcripción automáticamente…*" : text,
    };
    const newMessages = [...messages, userMsg];
    onMessages(newMessages);
    setInput("");
    setStreaming(true);

    // Placeholder del asistente
    const assistantMsg: ChatMessage = { role: "assistant", content: "" };
    const withAssistant = [...newMessages, assistantMsg];
    onMessages(withAssistant);

    // Para el streaming usamos el prompt real (no el display "isAuto")
    const apiMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: isAuto ? text : text },
    ];

    try {
      let accumulated = "";
      for await (const token of chatStream(apiMessages, {
        transcription,
        model,
        host,
        systemPrompt,
      })) {
        accumulated += token;
        onMessages([
          ...newMessages,
          { role: "assistant", content: accumulated },
        ]);
      }
    } catch (err) {
      setError(String(err));
      onMessages(newMessages); // quitar placeholder vacío
    } finally {
      setStreaming(false);
    }
  }

  function handleReanalyze() {
    onMessages([]);
    sendMessage(
      "Acabo de transcribir un audio. Analiza el contenido, " +
        "haz un resumen claro y destaca los puntos más importantes.",
      true
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col h-[700px]">
      {/* Header con ajustes */}
      <div className="p-4 border-b space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">🤖 Chat con Ollama</h2>
          {transcription && (
            <button
              disabled={streaming}
              onClick={handleReanalyze}
              className="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-1 rounded-lg transition-colors disabled:opacity-50"
            >
              🔄 Re-analizar
            </button>
          )}
        </div>

        <div className="flex gap-2">
          <input
            value={host}
            onChange={(e) => setHost(e.target.value)}
            placeholder="http://localhost:11434"
            className="flex-1 border rounded-lg px-2 py-1 text-xs"
          />
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="border rounded-lg px-2 py-1 text-xs min-w-28"
            disabled={availableModels.length === 0}
          >
            {availableModels.length > 0 ? (
              availableModels.map((m) => <option key={m}>{m}</option>)
            ) : (
              <option value="">Cargando modelos...</option>
            )}
          </select>
        </div>

        <details className="text-xs">
          <summary className="cursor-pointer text-gray-400 hover:text-gray-600">
            System prompt
          </summary>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={3}
            className="mt-1 w-full border rounded-lg px-2 py-1 text-xs resize-none"
          />
        </details>
      </div>

      {/* Mensajes */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 thin-scroll">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 text-sm mt-8">
            {transcription
              ? "Transcripción lista. Escribe una pregunta o haz clic en Re-analizar."
              : "Transcribe un audio para analizarlo, o inicia una conversación libre."}
          </p>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm
                ${msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm whitespace-pre-wrap"
                  : "bg-gray-100 text-gray-800 rounded-bl-sm prose prose-sm max-w-none"
                }`}
            >
              {msg.role === "user" ? (
                msg.content
              ) : (
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-2" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-2" {...props} />,
                    li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                    h1: ({ node, ...props }) => <h1 className="text-lg font-bold mb-2 mt-3" {...props} />,
                    h2: ({ node, ...props }) => <h2 className="text-base font-bold mb-2 mt-2" {...props} />,
                    h3: ({ node, ...props }) => <h3 className="font-bold mb-1 mt-2" {...props} />,
                    code: ({ node, inline, ...props }) =>
                      inline ? (
                        <code className="bg-gray-200 px-2 py-0.5 rounded text-xs" {...props} />
                      ) : (
                        <code className="block bg-gray-200 p-2 rounded mb-2 text-xs overflow-x-auto" {...props} />
                      ),
                    blockquote: ({ node, ...props }) => (
                      <blockquote className="border-l-4 border-gray-400 pl-4 italic mb-2" {...props} />
                    ),
                    strong: ({ node, ...props }) => <strong className="font-bold" {...props} />,
                    em: ({ node, ...props }) => <em className="italic" {...props} />,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
              {msg.role === "assistant" && msg.content === "" && streaming && (
                <span className="inline-block w-2 h-3.5 bg-gray-400 animate-pulse ml-0.5" />
              )}
            </div>
          </div>
        ))}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3">
            ❌ {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            disabled={streaming}
            placeholder={
              transcription
                ? "Pregunta sobre la transcripción…"
                : "Chat libre con Ollama…"
            }
            rows={1}
            className="flex-1 border rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:bg-gray-50"
          />
          <button
            disabled={!input.trim() || streaming}
            onClick={() => sendMessage(input)}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white px-4 rounded-xl transition-colors font-medium text-sm"
          >
            {streaming ? "…" : "➤"}
          </button>
        </div>
        {availableModels.length === 0 && (
          <p className="text-xs text-amber-600 mt-1">
            ⚠️ Ollama sin conexión — verifica que esté activo en{" "}
            <code>{host}</code>
          </p>
        )}
      </div>
    </div>
  );
}
