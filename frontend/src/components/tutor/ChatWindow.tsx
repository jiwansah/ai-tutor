"use client";
import { useEffect, useRef, useState } from "react";
import { Send, Sparkles, History } from "lucide-react";
import { useTutor } from "@/hooks/useTutor";
import { MessageBubble } from "./MessageBubble";
import { ModeSelector } from "./ModeSelector";
import { ChapterPicker, type StudyScope } from "./ChapterPicker";
import { SessionSidebar } from "./SessionSidebar";
import { useTutorStore } from "@/lib/store";

export function ChatWindow() {
  const { messages, ask, loading, awaitingAnswers } = useTutor();
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("teaching");
  const [scope, setScope] = useState<StudyScope>({ subjectId: null, chapterId: null });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Tracks whether the current mode change came from loading a session
  // (so we shouldn't reset the session we just loaded).
  const suppressModeResetRef = useRef(false);

  // Store accessors
  const sessionId = useTutorStore((s) => s.sessionId);
  const resetSession = useTutorStore((s) => s.reset);
  const setSession = useTutorStore((s) => s.setSession);
  const addMessage = useTutorStore((s) => s.addMessage);
  const setAwaitingAnswers = useTutorStore((s) => s.setAwaitingAnswers);
  const [sessionScope, setSessionScope] = useState<StudyScope | null>(null);

  // When the user manually changes the mode, start a fresh session.
  useEffect(() => {
    if (suppressModeResetRef.current) {
      suppressModeResetRef.current = false;
      return;
    }
    if (sessionId) {
      resetSession();
      setSessionScope(null);
      setScope({ subjectId: null, chapterId: null });
      if (typeof window !== "undefined") {
        localStorage.removeItem("last_session_id");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Auto-scroll during streaming and on new messages.
  const lastMessage = messages[messages.length - 1];
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [
    messages.length,
    lastMessage?.content?.length ?? 0,
    lastMessage?.citations?.length ?? 0,
    loading,
  ]);

  // Persist the current session id so a refresh resumes it.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (sessionId) {
      localStorage.setItem("last_session_id", sessionId);
    } else {
      localStorage.removeItem("last_session_id");
    }
  }, [sessionId]);

  // On mount, resume the last session.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const lastSession = localStorage.getItem("last_session_id");
    if (!lastSession || sessionId) return;

    import("@/lib/sessionApi").then(({ getSession }) =>
      getSession(lastSession)
        .then((detail) => {
          applySessionDetail(detail);
        })
        .catch(() => {
          localStorage.removeItem("last_session_id");
        })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Helpers ─────────────────────────────────────────────────────

  function applySessionDetail(detail: {
    id: string;
    mode: string;
    subject_id: string | null;
    chapter_id: string | null;
    section_id: string | null;
    messages: Array<{ role: "user" | "tutor"; content: string; citations?: any[]; meta?: any }>;
  }) {
    suppressModeResetRef.current = true;
    resetSession();

    // ── Restore mode ────────────────────────────────────────────
    let restoredMode = detail.mode || "teaching";
    if (["teacher", "socratic", "hint", "doubt", "revision"].includes(restoredMode)) {
      restoredMode = "teaching";
    } else if (["practice", "homework"].includes(restoredMode)) {
      restoredMode = "quiz";
    }
    setMode(restoredMode);

    // ── Restore subject/chapter scope ───────────────────────────
    if (detail.subject_id || detail.chapter_id) {
      setSessionScope({
        subjectId: detail.subject_id,
        chapterId: detail.chapter_id,
      });
    } else {
      setSessionScope(null);
    }

    // ── Restore messages ────────────────────────────────────────
    setSession(detail.id);
    let awaiting = false;
    detail.messages.forEach((m) => {
      addMessage({
        role: m.role === "user" ? "user" : "tutor",
        content: m.content,
        citations: m.citations,
      });
      awaiting = !!m.meta?.awaiting_answers;
    });
    setAwaitingAnswers(awaiting);
  }

  async function handleSidebarSelect(id: string) {
    try {
      const { getSession } = await import("@/lib/sessionApi");
      const detail = await getSession(id);
      applySessionDetail(detail);
      setSidebarOpen(false);
    } catch {
      // swallow — could toast
    }
  }

  function handleNewChat() {
    resetSession();
    setAwaitingAnswers(false);
    setSessionScope(null);
    setScope({ subjectId: null, chapterId: null });
    if (typeof window !== "undefined") {
      localStorage.removeItem("last_session_id");
    }
    setSidebarOpen(false);
  }

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
    <div className="h-full flex overflow-hidden">
      {/* Session history sidebar */}
      <SessionSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentSessionId={sessionId}
        onSelect={handleSidebarSelect}
        onNewChat={handleNewChat}
      />

      {/* Chat column */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden bg-white">
        <div className="flex-shrink-0 border-b bg-white px-3 sm:px-6 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-gray-100"
              aria-label="Conversation history"
              title="Conversation history"
            >
              <History className="w-4 h-4 text-gray-700" />
            </button>
            <div className="flex items-center gap-2 mr-1">
              <Sparkles className="w-4 h-4 text-indigo-600 hidden sm:block" />
              <ModeSelector value={mode} onChange={setMode} />
            </div>
            <ChapterPicker value={sessionScope} onChange={setScope} />
          </div>
        </div>

        {awaitingAnswers && (
          <div className="flex-shrink-0 bg-blue-50 border-b border-blue-200 px-3 sm:px-6 py-2 text-xs text-blue-900">
            📝 Answer the questions above — I'll grade them and show your score.
          </div>
        )}

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
    </div>
  );
}
