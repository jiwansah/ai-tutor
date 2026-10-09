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

export function ChapterPicker({ onChange }: { onChange: (s: StudyScope) => void }) {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [chapterId, setChapterId] = useState("");
  const [loading, setLoading] = useState(false);

  const classId = user?.class_id;
  const isStudent = user?.role === "student";

  useEffect(() => {
    if (!isStudent || !classId) return;
    setLoading(true);
    api.get(`/curriculum/subjects/${classId}`)
      .then((r) => setSubjects(r.data))
      .catch(() => setSubjects([]))
      .finally(() => setLoading(false));
  }, [classId, isStudent]);

  useEffect(() => {
    setChapterId("");
    setChapters([]);
    onChange({ subjectId: subjectId || null, chapterId: null });
    if (!subjectId) return;
    api.get(`/curriculum/chapters/${subjectId}`)
      .then((r) => setChapters(r.data))
      .catch(() => setChapters([]));
  }, [subjectId]);
  // eslint-disable-next-line react-hooks/exhaustive-deps

  if (!isStudent || !classId) return null;

  function handleChapterChange(id: string) {
    setChapterId(id);
    onChange({ subjectId: subjectId || null, chapterId: id || null });
  }

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
        onChange={(e) => handleChapterChange(e.target.value)}
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
