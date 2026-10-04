import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: false,
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Types
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

export async function submitAnswer(payload: {
  session_id: string;
  question: string;
  student_answer: string;
}) {
  const { data } = await api.post("/tutor/answer", payload);
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