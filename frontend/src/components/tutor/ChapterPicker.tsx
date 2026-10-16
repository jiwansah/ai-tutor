"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/store";

interface Subject { id: string; name: string }
interface Chapter { id: string; number: number; title: string }

export interface StudyScope {
  subjectId: string | null;
  chapterId: string | null;
}

export function ChapterPicker({
  value,
  onChange,
}: {
  value?: StudyScope | null;
  onChange: (s: StudyScope) => void;
}) {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [chapterId, setChapterId] = useState("");
  const [loading, setLoading] = useState(false);

  const classId = user?.class_id;
  const isStudent = user?.role === "student";

  // Load subjects on mount
  useEffect(() => {
    if (!isStudent || !classId) return;
    setLoading(true);
    api.get(`/curriculum/subjects/${classId}`)
      .then((r) => setSubjects(r.data))
      .catch(() => setSubjects([]))
      .finally(() => setLoading(false));
  }, [classId, isStudent]);

  // Sync from external `value` when a session is loaded
  useEffect(() => {
    if (!value) return;
    setSubjectId(value.subjectId ?? "");
    setChapterId(value.chapterId ?? "");
  }, [value?.subjectId, value?.chapterId]);

  // Load chapters whenever subject changes
  useEffect(() => {
    setChapterId("");
    setChapters([]);
    if (!subjectId) {
      onChange({ subjectId: null, chapterId: null });
      return;
    }
    api.get(`/curriculum/chapters/${subjectId}`)
      .then((r) => setChapters(r.data))
      .catch(() => setChapters([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjectId]);

  // Sync chapter selection back to parent when it changes
  useEffect(() => {
    onChange({ subjectId: subjectId || null, chapterId: chapterId || null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjectId, chapterId]);

  if (!isStudent || !classId) return null;

  return (
    <>
      <select
        value={subjectId}
        onChange={(e) => setSubjectId(e.target.value)}
        disabled={loading || subjects.length === 0}
        aria-label="Subject"
        className="rounded-lg border border-gray-300 px-2.5 py-2 text-sm bg-white min-h-[40px] flex-1 min-w-[120px] disabled:opacity-60"
      >
        <option value="">
          {loading ? "Loading…" :
           subjects.length === 0 ? "No subjects" : "Subject…"}
        </option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      <select
        value={chapterId}
        onChange={(e) => setChapterId(e.target.value)}
        disabled={!subjectId}
        aria-label="Chapter"
        className="rounded-lg border border-gray-300 px-2.5 py-2 text-sm bg-white min-h-[40px] flex-1 min-w-[120px] disabled:opacity-60"
      >
        <option value="">Chapter…</option>
        {chapters.map((c) => (
          <option key={c.id} value={c.id}>Ch {c.number}: {c.title}</option>
        ))}
      </select>
    </>
  );
}
