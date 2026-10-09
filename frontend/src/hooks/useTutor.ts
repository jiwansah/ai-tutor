"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useTutorStore } from "@/lib/store";
import { useTutorStream, type Citation, type Verification } from "./useTutorStream";

export interface AskOptions {
  mode?: string;
  subject_id?: string;
  chapter_id?: string;
  section_id?: string;
}

export function useTutor() {
  const {
    messages, addMessage, sessionId, setSession,
    appendToLastTutor, setCitationsOnLastTutor, setVerificationOnLastTutor,
    awaitingAnswers, setAwaitingAnswers,
  } = useTutorStore();
  const { stream, isStreaming } = useTutorStream();
  const [loading, setLoading] = useState(false);
  const [noContextWarning, setNoContextWarning] = useState<string | null>(null);

  async function ask(question: string, opts: AskOptions = {}) {
    if (!question.trim()) return;

    // ── If we're awaiting answers → grade this instead of asking ──
    if (awaitingAnswers && sessionId) {
      await submitAnswer(question, opts);
      return;
    }

    setNoContextWarning(null);
    addMessage({ role: "user", content: question });
    addMessage({ role: "tutor", content: "" });
    setLoading(true);

    await stream(
      {
        question,
        session_id: sessionId ?? undefined,
        mode: opts.mode ?? "teacher",
        subject_id: opts.subject_id,
        chapter_id: opts.chapter_id,
        section_id: opts.section_id,
      },
      {
        onSession: (id) => { if (!sessionId) setSession(id); },
        onToken: (text) => appendToLastTutor(text),
        onCitations: (citations: Citation[]) => setCitationsOnLastTutor(citations),
        onVerification: (v: Verification) => setVerificationOnLastTutor(v),
        onNoContext: (msg: string) => setNoContextWarning(msg),
        onDone: ({ awaiting_answers }) => {
          setAwaitingAnswers(!!awaiting_answers);
          setLoading(false);
        },
        onError: () => setLoading(false),
      },
    );

    setLoading(false);
  }

  async function submitAnswer(answer: string, opts: AskOptions) {
    if (!sessionId) return;

    addMessage({ role: "user", content: answer });
    setLoading(true);
    try {
      const { data } = await api.post("/tutor/answer", {
        session_id: sessionId,
        question: answer,
        student_answer: answer,
        concept_key: null,   // backend fetches from session
      });

      const score = data.score_percent ?? 0;
      const isCorrect = !!data.is_correct;
      const fb = data.feedback || (isCorrect ? "Correct!" : "Keep trying.");

      const reply =
        `${isCorrect ? "✅" : "📊"} **Score: ${score}%**\n\n${fb}`;

      addMessage({ role: "tutor", content: reply });

      // After grading, we're no longer awaiting answers
      setAwaitingAnswers(false);
    } catch (e: any) {
      addMessage({
        role: "tutor",
        content: "Sorry, I couldn't grade that. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  }

  async function askNewTopic() {
    setAwaitingAnswers(false);
  }

  return { messages, ask, askNewTopic, loading: loading || isStreaming, noContextWarning, awaitingAnswers };
}