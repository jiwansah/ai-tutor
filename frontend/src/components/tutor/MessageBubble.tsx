"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, CheckCircle2, XCircle } from "lucide-react";

interface Citation {
  chapter: string;
  section: string;
  page: number;
}

interface Verification {
  verified: boolean | null;
  sympy_solutions?: string[];
  llm_answer?: string | null;
  reason?: string;
}

interface Props {
  role: "user" | "tutor";
  content: string;
  citations?: Citation[];
  verification?: Verification;
  streaming?: boolean;
}

export function MessageBubble({ role, content, citations, verification, streaming }: Props) {
  const isUser = role === "user";
  const isEmpty = !content.trim();

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-900"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            {isEmpty && streaming ? (
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.15s]" />
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.3s]" />
                <span className="ml-2">Thinking…</span>
              </div>
            ) : (
              <>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                {streaming && (
                  <span className="inline-block w-[2px] h-[1em] bg-indigo-500 align-middle animate-pulse ml-0.5" />
                )}
              </>
            )}
          </div>
        )}

        {/* Verification badge */}
        {verification && verification.verified !== null && (
          <div className="mt-3">
            {verification.verified ? (
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-green-50 text-green-700 text-xs font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Verified by SymPy
                {verification.sympy_solutions && verification.sympy_solutions.length > 0 && (
                  <span className="text-green-600 font-normal">
                    · x = {verification.sympy_solutions.join(", ")}
                  </span>
                )}
              </div>
            ) : (
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-50 text-amber-700 text-xs font-medium">
                <XCircle className="w-3.5 h-3.5" />
                Could not verify
                {verification.reason && (
                  <span className="text-amber-600 font-normal">· {verification.reason}</span>
                )}
              </div>
            )}
          </div>
        )}

        {citations && citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-300 space-y-1">
            {citations.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                <BookOpen className="w-3 h-3" />
                <span>
                  {c.chapter} · {c.section} · p. {c.page}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
