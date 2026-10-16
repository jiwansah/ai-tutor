import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: any | null;
  setAuth: (token: string, user: any, refreshToken?: string) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,

      setAuth: (token, user, refreshToken) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", token);
          if (refreshToken) {
            localStorage.setItem("refresh_token", refreshToken);
          }
        }
        set({
          token,
          user,
          refreshToken: refreshToken ?? (typeof window !== "undefined"
            ? localStorage.getItem("refresh_token")
            : null),
        });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
        set({ token: null, refreshToken: null, user: null });
      },
    }),
    { name: "auth-store" },
  ),
);

// ─────────────────────────────────────────────────────────────────────
// Tutor store — unchanged, but kept for reference
// ─────────────────────────────────────────────────────────────────────

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

export interface ChatMessage {
  role: "user" | "tutor";
  content: string;
  citations?: Citation[];
  verification?: Verification;
}

interface TutorState {
  sessionId: string | null;
  messages: ChatMessage[];
  awaitingAnswers: boolean;
  addMessage: (m: ChatMessage) => void;
  appendToLastTutor: (text: string) => void;
  setCitationsOnLastTutor: (citations: Citation[]) => void;
  setVerificationOnLastTutor: (v: Verification) => void;
  setAwaitingAnswers: (v: boolean) => void;
  setSession: (id: string) => void;
  reset: () => void;
}

export const useTutorStore = create<TutorState>((set) => ({
  sessionId: null,
  messages: [],
  awaitingAnswers: false,

  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),

  appendToLastTutor: (text) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "tutor") {
          msgs[i] = { ...msgs[i], content: msgs[i].content + text };
          break;
        }
      }
      return { messages: msgs };
    }),

  setCitationsOnLastTutor: (citations) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "tutor") {
          msgs[i] = { ...msgs[i], citations };
          break;
        }
      }
      return { messages: msgs };
    }),

  setVerificationOnLastTutor: (verification) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "tutor") {
          msgs[i] = { ...msgs[i], verification };
          break;
        }
      }
      return { messages: msgs };
    }),

  setAwaitingAnswers: (v) => set({ awaitingAnswers: v }),
  setSession: (id) => set({ sessionId: id }),
  reset: () => set({ sessionId: null, messages: [], awaitingAnswers: false }),
}));