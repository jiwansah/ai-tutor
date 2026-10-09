import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  user: any | null;
  setAuth: (token: string, user: any) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        if (typeof window !== "undefined") localStorage.setItem("access_token", token);
        set({ token, user });
      },
      logout: () => {
        if (typeof window !== "undefined") localStorage.removeItem("access_token");
        set({ token: null, user: null });
      },
    }),
    { name: "auth-store" },
  ),
);

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
  awaitingAnswers?: boolean;    // NEW
}

interface TutorState {
  sessionId: string | null;
  messages: ChatMessage[];
  awaitingAnswers: boolean;                                      // NEW
  addMessage: (m: ChatMessage) => void;
  appendToLastTutor: (text: string) => void;
  setCitationsOnLastTutor: (citations: Citation[]) => void;
  setVerificationOnLastTutor: (v: Verification) => void;
  setAwaitingAnswers: (v: boolean) => void;                      // NEW
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
  reset: () => set({ sessionId: null, messages: [] }),
}));
