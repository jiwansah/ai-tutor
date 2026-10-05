"use client";
import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { useTutor } from "@/hooks/useTutor";
import { MessageBubble } from "./MessageBubble";
import { ModeSelector } from "./ModeSelector";

export function ChatWindow() {
  const { messages, ask, loading } = useTutor();
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("teacher");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const q = input;
    setInput("");
    await ask(q, { mode });
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <h1 className="font-semibold text-lg">AI Tutor</h1>
        </div>
        <ModeSelector value={mode} onChange={setMode} />
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-lg">Ask me anything from your textbook</p>
            <p className="text-sm mt-2">I'll teach you step by step</p>
          </div>
        )}
        {messages.map((m, i) => {
          const isLastTutor =
            m.role === "tutor" && i === messages.length - 1 && loading;
          return (
            <MessageBubble
              key={i}
              role={m.role}
              content={m.content}
              citations={m.citations}
              verification={m.verification}
              streaming={isLastTutor}
            />
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div className="border-t px-6 py-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question… (Shift+Enter for new line)"
            rows={2}
            disabled={loading}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="self-end rounded-lg bg-indigo-600 text-white px-4 py-2 font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
