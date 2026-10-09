"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  api,
  listPublicSchools,
  listPublicClasses,
} from "@/lib/api";
import { useAuth } from "@/lib/store";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी (Hindi)" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "te", label: "తెలుగు (Telugu)" },
  { code: "bn", label: "বাংলা (Bengali)" },
];

const STYLES = [
  { id: "step_by_step",  label: "Step by step" },
  { id: "socratic",      label: "Socratic (ask me questions)" },
  { id: "with_examples", label: "With examples" },
];

interface School { id: string; name: string; board: string }
interface Cls    { id: string; grade: number }

export function ProfileForm() {
  const { user, setAuth, token } = useAuth();

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [language, setLanguage] = useState(user?.language ?? "en");
  const [preferredStyle, setPreferredStyle] = useState("step_by_step");

  const [schools, setSchools] = useState<School[]>([]);
  const [classes, setClasses] = useState<Cls[]>([]);
  const [schoolId, setSchoolId] = useState<string>("");
  const [classId, setClassId] = useState<string>("");
  const [originalSchoolId, setOriginalSchoolId] = useState<string>("");
  const [originalClassId, setOriginalClassId] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [loadingClasses, setLoadingClasses] = useState(false);

  const isStudent = user?.role === "student";

  // Load profile + schools on mount
  useEffect(() => {
    if (!token) return;
    api.get("/auth/me").then((r) => {
      setFullName(r.data.full_name);
      setLanguage(r.data.language);
      if (r.data.preferred_style) setPreferredStyle(r.data.preferred_style);
      if (r.data.school_id) setSchoolId(r.data.school_id);
      if (r.data.class_id) setClassId(r.data.class_id);
      setOriginalSchoolId(r.data.school_id ?? "");
      setOriginalClassId(r.data.class_id ?? "");
    }).catch(() => {});

    if (isStudent) {
      listPublicSchools().then(setSchools).catch(() => {});
    }
  }, [token, isStudent]);

  // Load classes when school changes
  useEffect(() => {
    if (!schoolId) { setClasses([]); return; }
    setLoadingClasses(true);
    listPublicClasses(schoolId)
      .then((rows) => {
        setClasses(rows);
        // If current class isn't in this school's list, clear it
        if (classId && !rows.some((c) => c.id === classId)) {
          setClassId("");
        }
      })
      .catch(() => setClasses([]))
      .finally(() => setLoadingClasses(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schoolId]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();

    if (isStudent && (!schoolId || !classId)) {
      toast.error("Please select a school and class");
      return;
    }

    setLoading(true);
    try {
      const payload: any = { full_name: fullName, language };
      if (isStudent) {
        payload.preferred_style = preferredStyle;
        // Only send enrollment if changed
        if (schoolId !== originalSchoolId || classId !== originalClassId) {
          payload.school_id = schoolId;
          payload.class_id = classId;
        }
      }

      const { data } = await api.patch("/auth/me", payload);

      if (token) setAuth(token, data);
      setOriginalSchoolId(data.school_id ?? "");
      setOriginalClassId(data.class_id ?? "");
      toast.success("Profile updated");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to update");
    } finally {
      setLoading(false);
    }
  }

  const enrollmentChanged =
    isStudent &&
    (schoolId !== originalSchoolId || classId !== originalClassId);

  return (
    <form onSubmit={handleSave} className="rounded-xl border bg-white p-6 space-y-4">
      <h2 className="font-semibold text-lg">Profile</h2>

      <div className="space-y-1">
        <label className="text-sm text-gray-600">Email</label>
        <input value={user?.email ?? ""} disabled
          className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500" />
        <p className="text-xs text-gray-400">Email cannot be changed</p>
      </div>

      <div className="space-y-1">
        <label className="text-sm text-gray-600">Full name</label>
        <input value={fullName} onChange={(e) => setFullName(e.target.value)}
          required minLength={1} maxLength={120}
          className="w-full border rounded-lg px-3 py-2 text-sm" />
      </div>

      {isStudent && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t">
          <div className="space-y-1">
            <label className="text-sm text-gray-600">School</label>
            <select value={schoolId} onChange={(e) => setSchoolId(e.target.value)}
              required
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white">
              <option value="">— Select school —</option>
              {schools.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.board})</option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-sm text-gray-600">Class</label>
            <select value={classId} onChange={(e) => setClassId(e.target.value)}
              required
              disabled={!schoolId || loadingClasses}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white disabled:bg-gray-50">
              <option value="">
                {loadingClasses ? "Loading…" :
                 !schoolId ? "Pick a school first" :
                 classes.length === 0 ? "No classes available" :
                 "— Select class —"}
              </option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>Class {c.grade}</option>
              ))}
            </select>
          </div>

          {enrollmentChanged && (
            <div className="md:col-span-2 rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-900">
              ⓘ You're changing your class. Your progress on concepts you've
              already studied will be kept.
            </div>
          )}
        </div>
      )}

      <div className="space-y-1">
        <label className="text-sm text-gray-600">Language</label>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm bg-white">
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>{l.label}</option>
          ))}
        </select>
      </div>

      {isStudent && (
        <div className="space-y-1">
          <label className="text-sm text-gray-600">Preferred learning style</label>
          <select value={preferredStyle} onChange={(e) => setPreferredStyle(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm bg-white">
            {STYLES.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400">
            The tutor uses this as a hint when explaining concepts.
          </p>
        </div>
      )}

      <div className="flex justify-end">
        <button disabled={loading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
          {loading ? "Saving…" : "Save profile"}
        </button>
      </div>
    </form>
  );
}
