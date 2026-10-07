"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { listConcepts, createConcept, deleteConcept } from "@/lib/teacherApi";

export default function ConceptsPage() {
  const [concepts, setConcepts] = useState<any[]>([]);
  const [form, setForm] = useState({
    key: "", name: "", description: "", primary_section_id: "",
    learning_objectives: "",
  });

  useEffect(() => { load(); }, []);

  async function load() { try { setConcepts(await listConcepts()); } catch { toast.error("Failed to load"); } }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const objectives = form.learning_objectives.split("\n").map(s => s.trim()).filter(Boolean);
    try {
      await createConcept({
        key: form.key, name: form.name,
        description: form.description || null,
        primary_section_id: form.primary_section_id || null,
        learning_objectives: objectives,
      });
      toast.success("Concept created");
      setForm({ key: "", name: "", description: "", primary_section_id: "", learning_objectives: "" });
      await load();
    } catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }

  async function handleDelete(key: string) {
    if (!confirm(`Delete concept "${key}"?`)) return;
    try { await deleteConcept(key); toast.success("Deleted"); await load(); }
    catch { toast.error("Delete failed"); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Concepts</h1>
        <p className="text-gray-600 text-sm">Define learning objectives and link them to sections.</p>
      </div>

      <div className="rounded-xl border bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-2">Key</th>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Objectives</th>
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
                <td className="px-4 py-2 text-gray-600">{c.learning_objectives?.length || 0} objectives</td>
                <td className="px-4 py-2 text-right">
                  <Link href={`/teacher/concepts/${c.key}`} className="text-emerald-600 hover:underline mr-3">Edit</Link>
                  <button onClick={() => handleDelete(c.key)} className="text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="font-semibold mb-3">Create New Concept</h2>
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
          <input placeholder="Primary section ID (optional, UUID)" value={form.primary_section_id}
            onChange={(e) => setForm({ ...form, primary_section_id: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm font-mono text-xs" />
          <textarea placeholder="Learning objectives (one per line)" value={form.learning_objectives} rows={3}
            onChange={(e) => setForm({ ...form, learning_objectives: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
          <button className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm">Create</button>
        </form>
      </div>
    </div>
  );
}
