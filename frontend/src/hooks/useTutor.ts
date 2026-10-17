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

/**
 * Heuristic: does the text look like an answer to a pending assessment,
 * rather than a fresh question?
 */
function looksLikeAnswer(text: string): boolean {
  const t = (text || "").trim();
  if (!t) return false;

  // Question-shaped → not an answer
  if (/^(?:what|why|how|who|when|where|which|can you|could you|explain|tell me|help|please|show me)/i.test(t)) {
    return false;
  }
  if (t.includes("?")) return false;

  // MCQ answer pattern: "1 A, 2 B, 3 C" or "1) A  2) B"
  if (/^\s*\d+\s*[.)\-:]?\s*[A-Da-d]\b/m.test(t)) return true;

  // Value answer pattern: "1. x=4\n2. y=5" or "1 x=4"
  if (/^\s*\d+\s*[.)\-:]?\s*.+=.+/m.test(t)) return true;

  // Bare letters: "A, B, C" or "AB C"
  if (/^\s*[A-Da-d](?:\s*[,\s]\s*[A-Da-d])*\s*$/.test(t)) return true;

  // Short single-line text under 300 chars without paragraph breaks
  if (t.length < 300 && !t.includes("\n\n")) return true;

  return false;
}

export function useTutor() {
  const {
    messages,
    addMessage,
    sessionId,
    setSession,
    appendToLastTutor,
    setCitationsOnLastTutor,
    setVerificationOnLastTutor,
    // ─── Read & write awaiting flag from the shared Zustand store ───
    awaitingAnswers,
    setAwaitingAnswers,
  } = useTutorStore();

  const { stream, isStreaming } = useTutorStream();
  const [loading, setLoading] = useState(false);

  async function ask(question: string, opts: AskOptions = {}) {
    if (!question.trim()) return;

    // If the tutor is waiting for answers AND the input looks like an answer,
    // route to the grading endpoint instead of the streaming chat endpoint.
    if (awaitingAnswers && sessionId && looksLikeAnswer(question)) {
      await submitAnswer(question);
      return;
    }

    addMessage({ role: "user", content: question });
    addMessage({ role: "tutor", content: "" });
    setLoading(true);

    await stream(
      {
        question,
        session_id: sessionId ?? undefined,
        mode: opts.mode ?? "teaching",
        subject_id: opts.subject_id,
        chapter_id: opts.chapter_id,
        section_id: opts.section_id,
      },
      {
        onSession: (id) => {
          if (!sessionId) setSession(id);
        },
        onToken: (text) => appendToLastTutor(text),
        onCitations: (citations: Citation[]) => setCitationsOnLastTutor(citations),
        onVerification: (v: Verification) => setVerificationOnLastTutor(v),
        onDone: ({ awaiting_answers }) => {
          // The stream knows whether the tutor just asked questions.
          setAwaitingAnswers(!!awaiting_answers);
          setLoading(false);
        },
        onError: () => setLoading(false),
      },
    );

    setLoading(false);
  }

  async function submitAnswer(answer: string) {
    if (!sessionId) return;

    addMessage({ role: "user", content: answer });
    addMessage({ role: "tutor", content: "" });
    setLoading(true);

    try {
      const { data } = await api.post("/tutor/answer", {
        session_id: sessionId,
        question: "answer",
        student_answer: answer,
      });

      const correct = data.is_correct;
      const score = data.score_percent ?? 0;
      const feedback = data.feedback || "";
      const perQ = data.per_question_correct || [];
      const correct_answers = data.correct_answers || [];
      const student_answers = data.student_answers || [];

      const emoji = correct ? "✅" : score >= 50 ? "📊" : "📉";
      let body = `${emoji} **Score: ${score}%**\n\n${feedback}\n\n`;

      if (correct_answers.length > 0) {
        body += "---\n\n**Correct answers:**\n";
        correct_answers.forEach((right: string, i: number) => {
          const mark = perQ[i] ? "✅" : "❌";
          const yours = student_answers[i] ?? "—";
          body += `\n${mark} **Q${i + 1}**\n`;
          body += `You said: ${yours}\n`;
          body += `Correct: **${right}**\n`;
        });
      }

      appendToLastTutor(body);
      setAwaitingAnswers(false);
    } catch (e: any) {
      appendToLastTutor(
        e?.response?.data?.detail ||
          "Sorry, I couldn't grade that. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return {
    messages,
    ask,
    loading: loading || isStreaming,
    awaitingAnswers,
  };
}
