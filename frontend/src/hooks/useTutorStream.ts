"use client";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";   // ← reuse the axios baseURL logic

// Extract the resolved base URL from the axios instance
const API_URL = api.defaults.baseURL as string;

export interface Citation {
  chapter: string;
  section: string;
  page: number;
}

export interface Verification {
  verified: boolean | null;
  sympy_solutions?: string[];
  llm_answer?: string | null;
  reason?: string;
}

export interface StreamHandlers {
  onSession?: (sessionId: string) => void;
  onToken?: (text: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onVerification?: (v: Verification) => void;
  onDiagnostic?: (d: any) => void;
  onNoContext?: (msg: string) => void;
  onMode?: (info: { mode: string }) => void;
  onDone?: (info: { awaiting_answers?: boolean; effective_mode?: string }) => void;
  onError?: (message: string) => void;
}

export function useTutorStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const stream = useCallback(
    async (
      payload: {
        question: string;
        mode?: string;
        subject_id?: string;
        chapter_id?: string;
        section_id?: string;
        session_id?: string;
      },
      handlers: StreamHandlers,
    ) => {
      setIsStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("access_token")
            : null;

            async function doFetch(authToken: string | null) {
              return fetch(`${API_URL}/tutor/ask/stream`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
              });
            }

            let res = await doFetch(token);

            // If the token expired, try one refresh, then retry
            if (res.status === 401) {
              const refresh = typeof window !== "undefined"
                ? localStorage.getItem("refresh_token")
                : null;
              if (refresh) {
                try {
                  const refreshRes = await fetch(`${API_URL}/auth/refresh`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ refresh_token: refresh }),
                  });
                  if (refreshRes.ok) {
                    const data = await refreshRes.json();
                    localStorage.setItem("access_token", data.access_token);
                    if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
                    res = await doFetch(data.access_token);
                  }
                } catch {
                  // fall through to error handling below
                }
              }

              if (res.status === 401) {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                window.location.href = "/login";
                throw new Error("Session expired");
              }
            }

            if (!res.ok || !res.body) {
              const text = await res.text().catch(() => "");
              throw new Error(text || `HTTP ${res.status}`);
            }

        if (!res.ok || !res.body) {
          const text = await res.text().catch(() => "");
          throw new Error(text || `HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let idx: number;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const rawEvent = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);

            let eventName = "message";
            let dataStr = "";
            for (const line of rawEvent.split("\n")) {
              if (line.startsWith("event: ")) eventName = line.slice(7).trim();
              else if (line.startsWith("data: ")) dataStr += line.slice(6);
            }

            if (!dataStr) continue;
            let data: any = {};
            try {
              data = JSON.parse(dataStr);
            } catch {
              continue;
            }

            switch (eventName) {
              case "session":      handlers.onSession?.(data.session_id); break;
              case "token":        handlers.onToken?.(data.text ?? ""); break;
              case "citations":    handlers.onCitations?.(data.citations ?? []); break;
              case "verification": handlers.onVerification?.(data); break;
              case "diagnostic":   handlers.onDiagnostic?.(data); break;
              case "no_context":   handlers.onNoContext?.(data.message ?? ""); break;
              case "mode":         handlers.onMode?.(data); break;
              case "done":
                handlers.onDone?.({
                  awaiting_answers: data.awaiting_answers === true,
                  effective_mode: data.effective_mode,
                });
                break;
              case "error":
                handlers.onError?.(data.message ?? "Unknown error");
                break;
            }
          }
        }
      } catch (e: any) {
        if (e.name === "AbortError") return;
        toast.error(e?.message || "Streaming failed");
        handlers.onError?.(e?.message || "Streaming failed");
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [],
  );

  const abort = useCallback(() => abortRef.current?.abort(), []);

  return { stream, abort, isStreaming };
}
