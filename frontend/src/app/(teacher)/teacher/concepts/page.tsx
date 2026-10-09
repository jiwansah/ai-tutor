"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  listSchools, listClasses, listSubjects,
  listConcepts, createConcept, deleteConcept,
} from "@/lib/teacherApi";

export default function ConceptsPage() {
  const [concepts, setConcepts] = useState<any[]>([]);
  const [schools, setSchools] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);

  const [schoolId, setSchoolId] = useState("");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [isGlobal, setIsGlobal] = useState(false);

  const [form, setForm] = useState({
    key: "", name: "", description: "", learning_objectives: "",
  });

  // Initial load
  useEffect(() => { load(); loadSchools(); }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [classId]);

  async function load() {
    try {
      const data = await listConcepts(classId || undefined);
      setConcepts(data);
    } catch { toast.error("Failed to load concepts"); }
  }

  async function loadSchools() {
    try {
      const rows = await listSchools();
      setSchools(rows);
      if (rows[0]) setSchoolId(rows[0].id);
    } catch {}
  }

  useEffect(() => {
    setClassId(""); setClasses([]); setSubjects([]);
    if (!schoolId) return;
    listClasses(schoolId).then(setClasses).catch(() => {});
  }, [schoolId]);

  useEffect(() => {
    setSubjectId(""); setSubjects([]);
    if (!classId) return;
    listSubjects(classId).then(setSubjects).catch(() => {});
  }, [classId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!isGlobal && (!classId || !subjectId)) {
      toast.error("Pick class and subject, or mark as global");
      return;
    }
    const objectives = form.learning_objectives.split("\n").map(s => s.trim()).filter(Boolean);
    try {
      await createConcept({
        key: form.key,
        name: form.name,
        description: form.description || null,
        class_id: isGlobal ? null : (classId || null),
        subject_id: isGlobal ? null : (subjectId || null),
        learning_objectives: objectives,
      });
      toast.success("Concept created");
      setForm({ key: "", name: "", description: "", learning_objectives: "" });
      await load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  }

  async function handleDelete(key: string) {
    if (!confirm(`Delete concept "${key}"?`)) return;
    try { await deleteConcept(key); await load(); toast.success("Deleted"); }
    catch { toast.error("Delete failed"); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Concepts</h1>
        <p className="text-gray-600 text-sm">
          Learning objectives scoped to a class and subject. Global concepts (like inverse
          operations) apply to every class.
        </p>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap gap-3 items-center">
        <select value={schoolId} onChange={(e) => setSchoolId(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm">
          {schools.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <select value={classId} onChange={(e) => setClassId(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm">
          <option value="">— All classes —</option>
          {classes.map((c) => <option key={c.id} value={c.id}>Class {c.grade}</option>)}
        </select>
      </div>

      {/* List */}
      <div className="rounded-xl border bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-2">Key</th>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Scope</th>
              <th className="px-4 py-2 w-32"></th>
            </tr>
          </thead>
          <tbody>
            {concepts.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">No concepts yet</td></tr>
            )}
            {concepts.map((c) => (
              <tr key={c.key} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{c.key}</td>
                <td className="px-4 py-2">{c.name}</td>
                <td className="px-4 py-2">
                  {c.is_global
                    ? <span className="inline-block px-2 py-0.5 text-xs rounded bg-purple-50 text-purple-700">Global</span>
                    : <span className="inline-block px-2 py-0.5 text-xs rounded bg-emerald-50 text-emerald-700">Class-scoped</span>
                  }
                </td>
                <td className="px-4 py-2 text-right">
                  <Link href={`/teacher/concepts/${c.key}`} className="text-emerald-600 hover:underline mr-3">Edit</Link>
                  <button onClick={() => handleDelete(c.key)} className="text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create */}
      <div className="rounded-xl border bg-white p-5">
        <h2 className="font-semibold mb-3">Create New Concept</h2>

        <label className="flex items-center gap-2 mb-4 text-sm">
          <input type="checkbox" checked={isGlobal}
            onChange={(e) => setIsGlobal(e.target.checked)} />
          <span>Global concept (applies to every class — e.g., inverse operations)</span>
        </label>

        {!isGlobal && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            <select value={schoolId} onChange={(e) => setSchoolId(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm">
              {schools.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={classId} onChange={(e) => setClassId(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm">
              <option value="">— Class —</option>
              {classes.map((c) => <option key={c.id} value={c.id}>Class {c.grade}</option>)}
            </select>
            <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm" disabled={!classId}>
              <option value="">— Subject —</option>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        )}

        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input required placeholder="key (e.g. solving_linear_eq)" value={form.key}
              onChange={(e) => setForm({ ...form, key: e.target.value })}
              className="border rounded-lg px-3 py-2 text-sm font-mono" />
            <input required placeholder="Display name" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="border rounded-lg px-3 py-2 text-sm" />
          </div>
          <textarea placeholder="Description" value={form.description} rows={2}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
          <textarea placeholder="Learning objectives (one per line)" value={form.learning_objectives} rows={3}
            onChange={(e) => setForm({ ...form, learning_objectives: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
          <button className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm">
            Create
          </button>
        </form>
      </div>
    </div>
  );
}
