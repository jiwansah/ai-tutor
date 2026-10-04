"use client";
import { useState } from "react";
import { askTutor } from "@/lib/api";
import { useTutorStore } from "@/lib/store";
import { toast } from "sonner";

export function useTutor() {
  const [loading, setLoading] = useState(false);
  const { messages, addMessage, sessionId, setSession } = useTutorStore();

  async function ask(question: string, opts: { mode?: string; subject_id?: string } = {}) {
    if (!question.trim()) return;
    addMessage({ role: "user", content: question });
    setLoading(true);
    try {
      const res = await askTutor({ question, session_id: sessionId ?? undefined, ...opts });
      if (!sessionId) setSession(res.session_id);
      addMessage({ role: "tutor", content: res.answer, citations: res.citations });
      return res;
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return { messages, ask, loading };
}