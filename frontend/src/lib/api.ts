import axios from "axios";

/**
 * Determine the API base URL.
 *
 * Priority:
 *   1. NEXT_PUBLIC_API_URL env var (explicit override)
 *   2. Auto-detect: same hostname as the page, port 8000
 *      → works on localhost, LAN IP, or custom domain
 *
 * On the client, `window.location.hostname` gives us whatever the user typed.
 * If they opened http://192.168.1.42:3000, the API becomes http://192.168.1.42:8000/api/v1.
 */
function getApiBaseUrl(): string {
  // Server-side: fall back to env or localhost
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  }

  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  const host = window.location.hostname;

  // If env URL is set AND the current host matches it, use it
  if (envUrl && envUrl.includes(host)) {
    return envUrl;
  }

  // Auto-detect: use the same hostname as the browser, port 8000
  const protocol = window.location.protocol; // http: or https:
  // In production (port 443/80 via nginx), the API is on the same origin.
  // In dev, the backend lives on port 8000.
  if (window.location.port === "3000" || window.location.port === "") {
    // If accessed via port 3000 → backend is on port 8000 of the same host
    if (window.location.port === "3000") {
      return `${protocol}//${host}:8000/api/v1`;
    }
    // Port 80/443 → assume nginx proxies /api
    return `${protocol}//${host}/api/v1`;
  }

  // Fallback
  return envUrl || `http://${host}:8000/api/v1`;
}

const API_URL = getApiBaseUrl();

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
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ---- Types & helper functions (keep existing exports) ----

export interface AskResponse {
  session_id: string;
  answer: string;
  citations: { chapter: string; section: string; page: number }[];
  strategy?: string;
  mode?: string;
  concept_key: string | null;
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
  school_id?: string;
  class_id?: string;
}) {
  const { data } = await api.post("/auth/register", payload);
  return data;
}

export async function myProgress() {
  const { data } = await api.get("/dashboard/me/progress");
  return data;
}

export async function listChapters(subjectId: string) {
  const { data } = await api.get(`/curriculum/chapters/${subjectId}`);
  return data;
}

export async function listPublicSchools() {
  const { data } = await api.get("/public/schools");
  return data as { id: string; name: string; board: string }[];
}

export async function listPublicClasses(schoolId: string) {
  const { data } = await api.get(`/public/schools/${schoolId}/classes`);
  return data as { id: string; grade: number }[];
}
