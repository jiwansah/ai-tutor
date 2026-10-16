"use client";
import { useEffect, useState } from "react";
import { MessageSquare, Plus, Loader2, X } from "lucide-react";
import { listSessions, type SessionSummary } from "@/lib/sessionApi";

const MODE_BADGE: Record<string, string> = {
  teaching: "bg-indigo-50 text-indigo-700",
  quiz: "bg-emerald-50 text-emerald-700",
  exam: "bg-amber-50 text-amber-700",
  // legacy values
  teacher: "bg-indigo-50 text-indigo-700",
  socratic: "bg-indigo-50 text-indigo-700",
  hint: "bg-indigo-50 text-indigo-700",
  doubt: "bg-indigo-50 text-indigo-700",
  revision: "bg-indigo-50 text-indigo-700",
  practice: "bg-emerald-50 text-emerald-700",
};

function modeLabel(mode: string): string {
  if (["teacher", "socratic", "hint", "doubt", "revision", "teaching"].includes(mode)) return "Teaching";
  if (["practice", "homework", "quiz"].includes(mode)) return "Quiz";
  if (mode === "exam") return "Exam";
  return mode;
}

export function SessionSidebar({
  open,
  onClose,
  currentSessionId,
  onSelect,
  onNewChat,
}: {
  open: boolean;
  onClose: () => void;
  currentSessionId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    listSessions(30)
      .then(setSessions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open, currentSessionId]);

  if (!open) return null;

  return (
    <>
      {/* Overlay on mobile */}
      <div
        className="fixed inset-0 z-40 bg-black/30 md:hidden"
        onClick={onClose}
      />

      <aside className="fixed md:relative top-0 left-0 bottom-0 z-50 w-80 max-w-[85vw] bg-white border-r shadow-xl md:shadow-none flex flex-col">
        <div className="flex-shrink-0 h-14 px-4 border-b flex items-center justify-between">
          <span className="font-semibold">Conversations</span>
          <div className="flex items-center gap-2">
            <button
              onClick={onNewChat}
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
            >
              <Plus className="w-3 h-3" /> New
            </button>
            <button
              onClick={onClose}
              className="p-2 -mr-2 rounded-lg hover:bg-gray-100 md:hidden"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-gray-400 p-4">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading…
            </div>
          )}

          {!loading && sessions.length === 0 && (
            <div className="p-4 text-sm text-gray-500">
              No conversations yet. Ask a question to start one.
            </div>
          )}

          <ul className="divide-y">
            {sessions.map((s) => {
              const active = s.id === currentSessionId;
              const parts = [s.subject, s.chapter].filter(Boolean);
              const badgeClass = MODE_BADGE[s.mode] || "bg-gray-100 text-gray-700";

              return (
                <li key={s.id}>
                  <button
                    onClick={() => onSelect(s.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 ${
                      active ? "bg-indigo-50" : ""
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium truncate">
                          {s.preview || "(empty)"}
                        </div>
                        <div className="text-xs text-gray-500 truncate mt-0.5">
                          {parts.length > 0 ? parts.join(" · ") : "General"} ·{" "}
                          {new Date(s.created_at).toLocaleDateString()}
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${badgeClass}`}>
                            {modeLabel(s.mode)}
                          </span>
                          <span className="text-[10px] text-gray-400">
                            {s.message_count} messages
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </aside>
    </>
  );
}
