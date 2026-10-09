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
    if (awaitingAnswers && sessionId) {
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

      // Compose the result as a formatted message
      const correct = data.is_correct;
      const score = data.score_percent ?? 0;
      const feedback = data.feedback || "";
      const perQ = data.per_question_correct || [];
      const correct_answers = data.correct_answers || [];
      const student_answers = data.student_answers || [];

      const emoji = correct ? "✅" : score >= 50 ? "📊" : "📉";
      let body = `${emoji} **Score: ${score}%**\n\n${feedback}\n\n`;

      if (perQ.length > 0) {
        body += "**Breakdown:**\n";
        perQ.forEach((ok: boolean, i: number) => {
          const mark = ok ? "✅" : "❌";
          const yours = student_answers[i] ?? "—";
          const right = correct_answers[i] ?? "—";
          body += `${mark} Q${i + 1}: you said **${yours}**, correct was **${right}**\n`;
        });
      }

      // Replace the empty tutor bubble with the graded response
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
