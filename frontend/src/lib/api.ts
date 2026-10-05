import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const t = localStorage.getItem("access_token");
    if (t) config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

export interface AskResponse {
  session_id: string;
  answer: string;
  citations: { chapter: string; section: string; page: number }[];
  strategy: string;
  concept_key: string;
}

export async function askTutor(payload: {
  question: string;
  mode?: string;
  subject_id?: string;
  chapter_id?: string;
  section_id?: string;
  session_id?: string;
}): Promise<AskResponse> {
  const { data } = await api.post<AskResponse>("/tutor/ask", payload);
  return data;
}

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/login", { email, password });
  return data;
}

export async function register(payload: {
  email: string;
  password: string;
  full_name: string;
  role?: string;
}) {
  const { data } = await api.post("/auth/register", payload);
  return data;
}

export async function myProgress() {
  const { data } = await api.get("/dashboard/me/progress");
  return data;
}
