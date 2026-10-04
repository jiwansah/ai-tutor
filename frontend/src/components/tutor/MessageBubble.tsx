"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen } from "lucide-react";

interface Props {
  role: "user" | "tutor";
  content: string;
  citations?: { chapter: string; section: string; page: number }[];
}

export function MessageBubble({ role, content, citations }: Props) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-indigo-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
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