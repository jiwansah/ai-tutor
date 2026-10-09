"use client";
import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { useTutor } from "@/hooks/useTutor";
import { MessageBubble } from "./MessageBubble";
import { ModeSelector } from "./ModeSelector";
import { ChapterPicker, type StudyScope } from "./ChapterPicker";

export function ChatWindow() {
  const { messages, ask, loading, awaitingAnswers } = useTutor();
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("teacher");
  const [scope, setScope] = useState<StudyScope>({ subjectId: null, chapterId: null });
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const q = input;
    setInput("");
    await ask(q, {
      mode,
      subject_id: scope.subjectId ?? undefined,
      chapter_id: scope.chapterId ?? undefined,
    });
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-white">
      {/* Controls bar */}
      <div className="flex-shrink-0 border-b bg-white px-3 sm:px-6 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 mr-1">
            <Sparkles className="w-4 h-4 text-indigo-600 hidden sm:block" />
            <ModeSelector value={mode} onChange={setMode} />
          </div>
          <ChapterPicker onChange={setScope} />
        </div>
      </div>

      {/* Awaiting-answers banner */}
      {awaitingAnswers && (
        <div className="flex-shrink-0 bg-blue-50 border-b border-blue-200 px-3 sm:px-6 py-2 text-xs text-blue-900">
          📝 Answer the questions above — I'll grade them and show your score.
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollRef}
        className="chat-scroll flex-1 min-h-0 px-3 sm:px-6 py-4"
      >
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-16 sm:mt-20 px-6">
              <p className="text-base sm:text-lg">Ask me anything from your textbook</p>
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
        </div>
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t bg-white px-3 sm:px-6 py-3">
        <div className="flex gap-2 items-end max-w-4xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={awaitingAnswers
              ? "Type your answers (e.g. 1 B, 2 A, 3 C)…"
              : "Ask a question…"}
            rows={1}
            disabled={loading}
            className="flex-1 resize-none rounded-2xl border border-gray-300 px-4 py-2.5 text-base leading-6 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 max-h-32"
            style={{ minHeight: "44px" }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            aria-label="Send"
            className="flex-shrink-0 rounded-full bg-indigo-600 text-white w-11 h-11 flex items-center justify-center hover:bg-indigo-700 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
