"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  listConcepts, addPrerequisite, removePrerequisite,
  addMisconception, removeMisconception, updateConcept,
} from "@/lib/teacherApi";

export default function ConceptDetailPage() {
  const params = useParams<{ key: string }>();
  const router = useRouter();
  const key = decodeURIComponent(params.key);

  const [concept, setConcept] = useState<any>(null);
  const [allConcepts, setAllConcepts] = useState<any[]>([]);
  const [newPrereq, setNewPrereq] = useState("");
  const [newMisc, setNewMisc] = useState({ label: "", description: "", remedy: "" });
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [key]);

  async function load() {
    try {
      const [detail, all] = await Promise.all([
        api.get(`/concepts/${key}`).then(r => r.data),
        listConcepts(),
      ]);
      setConcept(detail);
      setAllConcepts(all);
      setEditName(detail.name);
      setEditDesc(detail.description || "");
    } catch { toast.error("Failed to load concept"); }
  }

  async function handleSaveMeta() {
    try {
      await updateConcept(key, { name: editName, description: editDesc });
      toast.success("Saved");
      await load();
    } catch { toast.error("Save failed"); }
  }

  async function handleAddPrereq(e: React.FormEvent) {
    e.preventDefault();
    if (!newPrereq) return;
    try {
      await addPrerequisite(key, newPrereq);
      setNewPrereq("");
      await load();
      toast.success("Prerequisite added");
    } catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }

  async function handleRemovePrereq(pk: string) {
    try { await removePrerequisite(key, pk); await load(); toast.success("Removed"); }
    catch { toast.error("Failed"); }
  }

  async function handleAddMisc(e: React.FormEvent) {
    e.preventDefault();
    try {
      await addMisconception(key, newMisc);
      setNewMisc({ label: "", description: "", remedy: "" });
      await load();
      toast.success("Added");
    } catch { toast.error("Failed"); }
  }

  async function handleRemoveMisc(id: string) {
    try { await removeMisconception(key, id); await load(); toast.success("Removed"); }
    catch { toast.error("Failed"); }
  }

  if (!concept) return <div className="text-gray-400">Loading…</div>;

  const availableForPrereq = allConcepts.filter(
    (c) => c.key !== key &&
      !concept.prerequisites.some((p: any) => p.key === c.key)
  );

  return (
    <div className="space-y-6">
      <button onClick={() => router.push("/teacher/concepts")} className="text-sm text-emerald-600 hover:underline">
        ← Back to concepts
      </button>

      <div>
        <div className="text-xs font-mono text-gray-500">{concept.key}</div>
        <input value={editName} onChange={(e) => setEditName(e.target.value)}
          className="text-2xl font-bold w-full border-b focus:outline-none focus:border-emerald-500" />
      </div>

      <div className="rounded-xl border bg-white p-5 space-y-4">
        <h2 className="font-semibold">Description</h2>
        <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={3}
          className="w-full border rounded-lg px-3 py-2 text-sm" />
        <button onClick={handleSaveMeta} className="bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-sm">
          Save
        </button>
      </div>

      <div className="rounded-xl border bg-white p-5 space-y-3">
        <h2 className="font-semibold">Prerequisites</h2>
        <ul className="space-y-2">
          {concept.prerequisites.length === 0 && <li className="text-sm text-gray-400">None yet</li>}
          {concept.prerequisites.map((p: any) => (
            <li key={p.key} className="flex items-center justify-between border rounded-lg px-3 py-2 text-sm">
              <span><span className="font-mono text-xs mr-2">{p.key}</span>{p.name}</span>
              <button onClick={() => handleRemovePrereq(p.key)} className="text-red-600 hover:underline text-xs">Remove</button>
            </li>
          ))}
        </ul>
        <form onSubmit={handleAddPrereq} className="flex gap-2">
          <select value={newPrereq} onChange={(e) => setNewPrereq(e.target.value)}
            className="flex-1 border rounded-lg px-3 py-2 text-sm">
            <option value="">— Select concept —</option>
            {availableForPrereq.map((c) => (
              <option key={c.key} value={c.key}>{c.name} ({c.key})</option>
            ))}
          </select>
          <button className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm">Add</button>
        </form>
      </div>

      <div className="rounded-xl border bg-white p-5 space-y-3">
        <h2 className="font-semibold">Misconceptions</h2>
        <ul className="space-y-2">
          {concept.misconceptions.length === 0 && <li className="text-sm text-gray-400">None yet</li>}
          {concept.misconceptions.map((m: any, i: number) => (
            <li key={i} className="border rounded-lg px-3 py-2 text-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-medium">{m.label}</span>
                <button onClick={() => handleRemoveMisc(m.id)} className="text-red-600 hover:underline text-xs">Remove</button>
              </div>
              {m.description && <div className="text-gray-600 text-xs">{m.description}</div>}
              {m.remedy && <div className="text-emerald-700 text-xs">Remedy: {m.remedy}</div>}
            </li>
          ))}
        </ul>
        <form onSubmit={handleAddMisc} className="space-y-2">
          <input required placeholder="Label (e.g. one_side_only)" value={newMisc.label}
            onChange={(e) => setNewMisc({ ...newMisc, label: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
          <input placeholder="Description" value={newMisc.description}
            onChange={(e) => setNewMisc({ ...newMisc, description: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
          <input placeholder="Remedy" value={newMisc.remedy}
            onChange={(e) => setNewMisc({ ...newMisc, remedy: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
          <button className="bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-sm">Add Misconception</button>
        </form>
      </div>
    </div>
  );
}
