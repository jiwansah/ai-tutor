"use client";
import { useState } from "react";
import { useTutorStore } from "@/lib/store";
import { useTutorStream, type Citation, type Verification } from "./useTutorStream";

export function useTutor() {
  const {
    messages,
    addMessage,
    sessionId,
    setSession,
    appendToLastTutor,
    setCitationsOnLastTutor,
    setVerificationOnLastTutor,
  } = useTutorStore();
  const { stream, isStreaming } = useTutorStream();
  const [loading, setLoading] = useState(false);

  async function ask(question: string, opts: { mode?: string; section_id?: string } = {}) {
    if (!question.trim()) return;

    addMessage({ role: "user", content: question });
    addMessage({ role: "tutor", content: "" });
    setLoading(true);

    await stream(
      {
        question,
        session_id: sessionId ?? undefined,
        mode: opts.mode ?? "teacher",
        section_id: opts.section_id,
      },
      {
        onSession: (id) => { if (!sessionId) setSession(id); },
        onToken: (text) => appendToLastTutor(text),
        onCitations: (citations: Citation[]) => setCitationsOnLastTutor(citations),
        onVerification: (v: Verification) => setVerificationOnLastTutor(v),
        onDone: () => setLoading(false),
        onError: () => setLoading(false),
      },
    );

    setLoading(false);
  }

  return { messages, ask, loading: loading || isStreaming };
}
