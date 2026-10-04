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
        localStorage.setItem("access_token", token);
        set({ token, user });
      },
      logout: () => {
        localStorage.removeItem("access_token");
        set({ token: null, user: null });
      },
    }),
    { name: "auth-store" }
  )
);

interface TutorState {
  sessionId: string | null;
  messages: { role: "user" | "tutor"; content: string; citations?: any[] }[];
  addMessage: (m: TutorState["messages"][number]) => void;
  setSession: (id: string) => void;
  reset: () => void;
}

export const useTutorStore = create<TutorState>((set) => ({
  sessionId: null,
  messages: [],
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  setSession: (id) => set({ sessionId: id }),
  reset: () => set({ sessionId: null, messages: [] }),
}));