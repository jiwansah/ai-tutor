"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Upload, FileText, CheckCircle2, XCircle, Loader2, Trash2 } from "lucide-react";
import { listSchools, listClasses, listSubjects, listBooks } from "@/lib/teacherApi";
import {
  uploadPdf, listJobs, deleteJob,
  type IngestJob,
} from "@/lib/ingestApi";

export default function IngestPage() {
  const [jobs, setJobs] = useState<IngestJob[]>([]);

  // Book picker state
  const [schools, setSchools] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [books, setBooks] = useState<any[]>([]);
  const [schoolId, setSchoolId] = useState("");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [bookId, setBookId] = useState("");

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initial load
  useEffect(() => {
    loadJobs();
    listSchools().then((rows) => {
      setSchools(rows);
      if (rows[0]) setSchoolId(rows[0].id);
    }).catch(() => {});
  }, []);

  // Cascade loaders
  useEffect(() => {
    setClassId(""); setClasses([]); setSubjects([]); setBooks([]); setSubjectId(""); setBookId("");
    if (!schoolId) return;
    listClasses(schoolId).then(setClasses).catch(() => {});
  }, [schoolId]);

  useEffect(() => {
    setSubjectId(""); setSubjects([]); setBooks([]); setBookId("");
    if (!classId) return;
    listSubjects(classId).then(setSubjects).catch(() => {});
  }, [classId]);

  useEffect(() => {
    setBookId(""); setBooks([]);
    if (!subjectId) return;
    listBooks(subjectId).then(setBooks).catch(() => {});
  }, [subjectId]);

  // Auto-refresh jobs while any is in-progress
  useEffect(() => {
    const anyActive = jobs.some((j) => j.status === "pending" || j.status === "parsing" || j.status === "publishing");
    if (!anyActive) return;
    const t = setInterval(loadJobs, 2000);
    return () => clearInterval(t);
  }, [jobs]);

  async function loadJobs() {
    try {
      const rows = await listJobs();
      setJobs(rows);
    } catch {
      // silent
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!bookId) {
      toast.error("Select a book first");
      return;
    }
    if (!file) {
      toast.error("Choose a PDF file");
      return;
    }
    setUploading(true);
    try {
      const job = await uploadPdf(bookId, file);
      toast.success("Uploaded — parsing in background");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadJobs();
      // Navigate to the job preview page
      window.location.href = `/teacher/ingest/${job.id}`;
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(jobId: string) {
    if (!confirm("Delete this job? Any parsed content from it will be discarded.")) return;
    try {
      await deleteJob(jobId);
      toast.success("Job deleted");
      await loadJobs();
    } catch {
      toast.error("Delete failed");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Bulk PDF Ingest</h1>
        <p className="text-gray-600 text-sm">
          Upload a textbook PDF. The system will parse chapters and sections. You review, then approve.
        </p>
      </div>

      {/* Upload form */}
      <form onSubmit={handleUpload} className="rounded-xl border bg-white p-5 space-y-4">
        <h2 className="font-semibold">Upload new PDF</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <select value={schoolId} onChange={(e) => setSchoolId(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm bg-white">
            {schools.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select value={classId} onChange={(e) => setClassId(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">— Class —</option>
            {classes.map((c) => <option key={c.id} value={c.id}>Class {c.grade}</option>)}
          </select>
          <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm bg-white" disabled={!classId}>
            <option value="">— Subject —</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select value={bookId} onChange={(e) => setBookId(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm bg-white" disabled={!subjectId}>
            <option value="">— Book —</option>
            {books.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
          </select>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100"
          />
          <button
            type="submit"
            disabled={uploading || !file || !bookId}
            className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {uploading ? "Uploading…" : "Upload & parse"}
          </button>
        </div>
        <p className="text-xs text-gray-500">Max 50 MB. PDFs only.</p>
      </form>

      {/* Job list */}
      <div className="rounded-xl border bg-white overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50 font-medium text-sm">
          Recent jobs
        </div>
        <ul className="divide-y">
          {jobs.length === 0 && (
            <li className="px-5 py-8 text-center text-gray-400 text-sm">No uploads yet</li>
          )}
          {jobs.map((job) => (
            <li key={job.id} className="px-5 py-3 flex flex-wrap items-center gap-3">
              <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Link href={`/teacher/ingest/${job.id}`}
                    className="font-medium text-sm truncate hover:text-emerald-600">
                    {job.filename}
                  </Link>
                  <StatusBadge status={job.status} />
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {job.page_count > 0 && <span>{job.page_count} pages · </span>}
                  <span>{job.file_size_kb} KB · </span>
                  <span>{new Date(job.created_at).toLocaleString()}</span>
                </div>
                {job.error_message && (
                  <div className="text-xs text-red-600 mt-1">{job.error_message}</div>
                )}
                {(job.status === "parsing" || job.status === "publishing") && (
                  <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 transition-all"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href={`/teacher/ingest/${job.id}`}
                  className="text-xs text-emerald-600 hover:underline whitespace-nowrap"
                >
                  {job.status === "preview_ready" ? "Review" : "View"}
                </Link>
                <button
                  onClick={() => handleDelete(job.id)}
                  className="text-red-500 hover:text-red-700 p-1"
                  aria-label="Delete job"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}


function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string; icon: any }> = {
    pending:        { label: "Pending",   className: "bg-gray-100 text-gray-700",     icon: Loader2 },
    parsing:        { label: "Parsing",   className: "bg-blue-50 text-blue-700",      icon: Loader2 },
    preview_ready:  { label: "Review",    className: "bg-amber-50 text-amber-800",    icon: FileText },
    publishing:     { label: "Publishing", className: "bg-indigo-50 text-indigo-700", icon: Loader2 },
    approved:       { label: "Approved",  className: "bg-green-50 text-green-700",    icon: CheckCircle2 },
    failed:         { label: "Failed",    className: "bg-red-50 text-red-700",        icon: XCircle },
  };
  const cfg = map[status] || { label: status, className: "bg-gray-100", icon: FileText };
  const Icon = cfg.icon;
  const spin = status === "parsing" || status === "publishing" || status === "pending";
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.className}`}>
      <Icon className={`w-3 h-3 ${spin ? "animate-spin" : ""}`} />
      {cfg.label}
    </span>
  );
}
