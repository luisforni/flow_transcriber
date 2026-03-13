"use client";

import { useState } from "react";
import TranscribePanel from "@/components/TranscribePanel";
import ChatPanel from "@/components/ChatPanel";
import type { Part, ChatMessage } from "@/lib/api";

export default function Home() {
  const [parts, setParts] = useState<Part[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [autoPrompt, setAutoPrompt] = useState("");
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434");

  const transcriptionText = parts.map((p) => p.content).join("\n\n");

  function handleResult(newParts: Part[], prompt: string) {
    setParts(newParts);
    setMessages([]);
    setAutoPrompt(prompt);
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight">🎙️ Flow Transcriber</h1>
        <p className="text-sm text-gray-500">
          Transcribe audio · Analiza con IA local (OLLAMA)
        </p>
      </header>

      <div className="max-w-6xl mx-auto p-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TranscribePanel
          parts={parts}
          ollamaHost={ollamaHost}
          onResult={handleResult}
        />
        <ChatPanel
          transcription={transcriptionText}
          messages={messages}
          onMessages={setMessages}
          autoPrompt={autoPrompt}
          onAutoPromptConsumed={() => setAutoPrompt("")}
        />
      </div>
    </main>
  );
}
