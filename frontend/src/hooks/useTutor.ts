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

function looksLikeAnswer(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  // If it starts with a question word or has "?", it's a new question
  if (/^(?:what|why|how|who|when|where|which|can you|explain|tell me|help|please)/i.test(t)) {
    return false;
  }
  if (t.includes("?")) return false;
  // If it looks like "1 A, 2 B" or "x=4" — treat as an answer
  if (/^\s*\d+\s*[\.")\-:]?\s*(?:[A-Da-d]|\d|[\w\u0900-\u097F])/m.test(t)) {
    return true;
  }
  // Short single-line responses are likely answers
  if (t.length < 120) return true;
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
  } = useTutorStore();
  const { stream, isStreaming } = useTutorStream();
  const [loading, setLoading] = useState(false);
  const [awaitingAnswers, setAwaitingAnswers] = useState(false);

  async function ask(question: string, opts: AskOptions = {}) {
    if (!question.trim()) return;

    // If the tutor is waiting for answers, route this to the grader
        // If the tutor is waiting for answers, route to the grader —
    // BUT only if the message looks like an answer, not a new question.
    if (awaitingAnswers && sessionId && looksLikeAnswer(question)) {
      await submitAnswer(question, opts);
      return;
    }

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
        onDone: ({ awaiting_answers }) => {
          // The tutor just asked questions → next user input is an answer
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
    addMessage({ role: "tutor", content: "" });
    setLoading(true);

    try {
      const { data } = await api.post("/tutor/answer", {
        session_id: sessionId,
        question: "answer to quiz",
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

      // After grading, stop waiting for more answers
      setAwaitingAnswers(false);
    } catch (e: any) {
      appendToLastTutor("Sorry, I couldn't grade that. Please try again.");
      setAwaitingAnswers(false);
    } finally {
      setLoading(false);
    }
  }

  return { messages, ask, loading: loading || isStreaming, awaitingAnswers };
}
