import { api } from "./api";

export interface SessionSummary {
  id: string;
  mode: string;
  subject: string | null;
  chapter: string | null;
  section: string | null;
  preview: string;
  message_count: number;
  created_at: string;
}

export interface SessionMessage {
  role: "user" | "tutor";
  content: string;
  citations?: { chapter: string; section: string; page: number }[];
  meta?: any;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  mode: string;
  subject_id: string | null;
  chapter_id: string | null;
  section_id: string | null;
  messages: SessionMessage[];
}

export async function listSessions(limit = 30): Promise<SessionSummary[]> {
  const { data } = await api.get(`/tutor/sessions?limit=${limit}`);
  return data;
}

export async function getSession(id: string): Promise<SessionDetail> {
  const { data } = await api.get(`/tutor/sessions/${id}`);
  return data;
}