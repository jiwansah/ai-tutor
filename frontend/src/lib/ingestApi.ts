import { api } from "./api";

export interface IngestJob {
  id: string;
  filename: string;
  status: "pending" | "parsing" | "preview_ready" | "publishing" | "approved" | "failed";
  progress: number;
  page_count: number;
  book_id: string;
  file_size_kb: number;
  error_message: string | null;
  created_at: string;
  published_at: string | null;
}

export interface Chunk {
  text: string;
  page: number;
}

export interface ParsedSection {
  number: string;
  title: string;
  start_page: number;
  end_page: number;
  chunks: Chunk[];
}

export interface ParsedChapter {
  number: number;
  title: string;
  start_page: number;
  end_page: number;
  sections: ParsedSection[];
}

export interface ParsedData {
  page_count: number;
  chapters: ParsedChapter[];
}


export async function uploadPdf(bookId: string, file: File): Promise<IngestJob> {
  const form = new FormData();
  form.append("book_id", bookId);
  form.append("file", file);
  // Do NOT set Content-Type manually. The browser/axios sets it with
  // the correct multipart boundary automatically.
  const { data } = await api.post("/teacher/ingest/upload", form, {
    timeout: 120_000,
  });
  return data;
}

export async function listJobs(): Promise<IngestJob[]> {
  const { data } = await api.get("/teacher/ingest/jobs");
  return data;
}

export async function getJob(jobId: string): Promise<IngestJob> {
  const { data } = await api.get(`/teacher/ingest/jobs/${jobId}`);
  return data;
}

export async function getPreview(jobId: string): Promise<ParsedData> {
  const { data } = await api.get(`/teacher/ingest/jobs/${jobId}/preview`);
  return data;
}

export async function updateParsed(jobId: string, parsedData: ParsedData): Promise<void> {
  await api.patch(`/teacher/ingest/jobs/${jobId}`, { parsed_data: parsedData });
}

export async function approveJob(jobId: string): Promise<{ status: string }> {
  const { data } = await api.post(`/teacher/ingest/jobs/${jobId}/approve`);
  return data;
}

export async function deleteJob(jobId: string): Promise<void> {
  await api.delete(`/teacher/ingest/jobs/${jobId}`);
}
