"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  listSchools, createSchool,
  listClasses, createClass,
  listSubjects, createSubject,
  listBooks, createBook,
  listChapters, createChapter,
  listSections, createSection,
} from "@/lib/teacherApi";

interface Node { id: string; name?: string; title?: string; grade?: number; number?: any; board?: string }

export default function CurriculumPage() {
  const [schools, setSchools] = useState<Node[]>([]);
  const [school, setSchool] = useState<Node | null>(null);
  const [classes, setClasses] = useState<Node[]>([]);
  const [cls, setCls] = useState<Node | null>(null);
  const [subjects, setSubjects] = useState<Node[]>([]);
  const [subj, setSubj] = useState<Node | null>(null);
  const [books, setBooks] = useState<Node[]>([]);
  const [book, setBook] = useState<Node | null>(null);
  const [chapters, setChapters] = useState<Node[]>([]);
  const [chap, setChap] = useState<Node | null>(null);
  const [sections, setSections] = useState<Node[]>([]);

  const [newSchool, setNewSchool] = useState({ name: "", board: "CBSE", city: "" });
  const [newClassGrade, setNewClassGrade] = useState("");
  const [newSubjectName, setNewSubjectName] = useState("");
  const [newBookTitle, setNewBookTitle] = useState("");
  const [newChapter, setNewChapter] = useState({ number: "", title: "" });
  const [newSection, setNewSection] = useState({ number: "", title: "", start_page: "", end_page: "" });

  useEffect(() => { loadSchools(); }, []);

  async function loadSchools() { try { setSchools(await listSchools()); } catch { toast.error("Failed to load schools"); } }
  async function loadClasses(s: Node) { setSchool(s); setCls(null); setSubjects([]); setBooks([]); setChapters([]); setSections([]); setClasses(await listClasses(s.id)); }
  async function loadSubjects(c: Node) { setCls(c); setSubj(null); setBooks([]); setChapters([]); setSections([]); setSubjects(await listSubjects(c.id)); }
  async function loadBooks(s: Node) { setSubj(s); setBook(null); setChapters([]); setSections([]); setBooks(await listBooks(s.id)); }
  async function loadChapters(b: Node) { setBook(b); setChap(null); setSections([]); setChapters(await listChapters(b.id)); }
  async function loadSections(c: Node) { setChap(c); setSections(await listSections(c.id)); }

  async function handleCreateSchool(e: React.FormEvent) {
    e.preventDefault();
    try { await createSchool(newSchool); setNewSchool({ name: "", board: "CBSE", city: "" }); await loadSchools(); toast.success("School created"); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }
  async function handleCreateClass(e: React.FormEvent) {
    e.preventDefault();
    if (!school || !newClassGrade) return;
    try { await createClass({ school_id: school.id, grade: parseInt(newClassGrade) }); setNewClassGrade(""); await loadClasses(school); toast.success("Class created"); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }
  async function handleCreateSubject(e: React.FormEvent) {
    e.preventDefault();
    if (!cls || !newSubjectName) return;
    try { await createSubject({ class_id: cls.id, name: newSubjectName }); setNewSubjectName(""); await loadSubjects(cls); toast.success("Subject created"); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }
  async function handleCreateBook(e: React.FormEvent) {
    e.preventDefault();
    if (!subj || !newBookTitle) return;
    try { await createBook({ subject_id: subj.id, title: newBookTitle }); setNewBookTitle(""); await loadBooks(subj); toast.success("Book created"); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }
  async function handleCreateChapter(e: React.FormEvent) {
    e.preventDefault();
    if (!book || !newChapter.number || !newChapter.title) return;
    try { await createChapter({ book_id: book.id, number: parseInt(newChapter.number), title: newChapter.title }); setNewChapter({ number: "", title: "" }); await loadChapters(book); toast.success("Chapter created"); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }
  async function handleCreateSection(e: React.FormEvent) {
    e.preventDefault();
    if (!chap || !newSection.number || !newSection.title) return;
    try {
      await createSection({
        chapter_id: chap.id,
        number: newSection.number,
        title: newSection.title,
        start_page: newSection.start_page ? parseInt(newSection.start_page) : undefined,
        end_page: newSection.end_page ? parseInt(newSection.end_page) : undefined,
      });
      setNewSection({ number: "", title: "", start_page: "", end_page: "" });
      await loadSections(chap);
      toast.success("Section created");
    } catch (e: any) { toast.error(e?.response?.data?.detail || "Failed"); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Curriculum</h1>
        <p className="text-gray-600 text-sm">Build the tree: School → Class → Subject → Book → Chapter → Section.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Schools */}
        <Column title="Schools" items={schools} selectedId={school?.id} onSelect={loadClasses} renderLabel={(n) => `${n.name} (${n.board})`} />
        <div className="space-y-3">
          <Column title="Classes" items={classes} selectedId={cls?.id} onSelect={loadSubjects} renderLabel={(n) => `Class ${n.grade}`} />
          <form onSubmit={handleCreateClass} className="flex gap-2">
            <input type="number" placeholder="Grade" value={newClassGrade} onChange={(e) => setNewClassGrade(e.target.value)}
              className="flex-1 border rounded-lg px-2 py-1 text-sm" disabled={!school} />
            <button disabled={!school} className="text-sm bg-emerald-600 text-white px-3 py-1 rounded-lg disabled:opacity-50">Add</button>
          </form>
        </div>
        <div className="space-y-3">
          <Column title="Subjects" items={subjects} selectedId={subj?.id} onSelect={loadBooks} renderLabel={(n) => n.name!} />
          <form onSubmit={handleCreateSubject} className="flex gap-2">
            <input placeholder="Name" value={newSubjectName} onChange={(e) => setNewSubjectName(e.target.value)}
              className="flex-1 border rounded-lg px-2 py-1 text-sm" disabled={!cls} />
            <button disabled={!cls} className="text-sm bg-emerald-600 text-white px-3 py-1 rounded-lg disabled:opacity-50">Add</button>
          </form>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-3">
          <Column title="Books" items={books} selectedId={book?.id} onSelect={loadChapters} renderLabel={(n) => n.title!} />
          <form onSubmit={handleCreateBook} className="flex gap-2">
            <input placeholder="Book title" value={newBookTitle} onChange={(e) => setNewBookTitle(e.target.value)}
              className="flex-1 border rounded-lg px-2 py-1 text-sm" disabled={!subj} />
            <button disabled={!subj} className="text-sm bg-emerald-600 text-white px-3 py-1 rounded-lg disabled:opacity-50">Add</button>
          </form>
        </div>
        <div className="space-y-3">
          <Column title="Chapters" items={chapters} selectedId={chap?.id} onSelect={loadSections} renderLabel={(n) => `Ch ${n.number}: ${n.title}`} />
          <form onSubmit={handleCreateChapter} className="flex gap-2">
            <input type="number" placeholder="No." value={newChapter.number}
              onChange={(e) => setNewChapter({ ...newChapter, number: e.target.value })}
              className="w-16 border rounded-lg px-2 py-1 text-sm" disabled={!book} />
            <input placeholder="Title" value={newChapter.title}
              onChange={(e) => setNewChapter({ ...newChapter, title: e.target.value })}
              className="flex-1 border rounded-lg px-2 py-1 text-sm" disabled={!book} />
            <button disabled={!book} className="text-sm bg-emerald-600 text-white px-3 py-1 rounded-lg disabled:opacity-50">Add</button>
          </form>
        </div>
        <div className="space-y-3">
          <Column title="Sections" items={sections} selectedId={null} onSelect={(() => {}) as any}
            renderLabel={(n) => `${n.number}: ${n.title}`} />
          <form onSubmit={handleCreateSection} className="space-y-1">
            <div className="flex gap-2">
              <input placeholder="No." value={newSection.number}
                onChange={(e) => setNewSection({ ...newSection, number: e.target.value })}
                className="w-16 border rounded-lg px-2 py-1 text-sm" disabled={!chap} />
              <input placeholder="Title" value={newSection.title}
                onChange={(e) => setNewSection({ ...newSection, title: e.target.value })}
                className="flex-1 border rounded-lg px-2 py-1 text-sm" disabled={!chap} />
            </div>
            <div className="flex gap-2">
              <input type="number" placeholder="Start pg" value={newSection.start_page}
                onChange={(e) => setNewSection({ ...newSection, start_page: e.target.value })}
                className="w-24 border rounded-lg px-2 py-1 text-sm" disabled={!chap} />
              <input type="number" placeholder="End pg" value={newSection.end_page}
                onChange={(e) => setNewSection({ ...newSection, end_page: e.target.value })}
                className="w-24 border rounded-lg px-2 py-1 text-sm" disabled={!chap} />
              <button disabled={!chap} className="text-sm bg-emerald-600 text-white px-3 py-1 rounded-lg disabled:opacity-50 ml-auto">Add</button>
            </div>
          </form>
        </div>
      </div>

      <div className="mt-8 border-t pt-6">
        <h2 className="text-lg font-semibold">Create School</h2>
        <form onSubmit={handleCreateSchool} className="flex flex-wrap gap-2 mt-3">
          <input placeholder="Name" value={newSchool.name}
            onChange={(e) => setNewSchool({ ...newSchool, name: e.target.value })}
            className="border rounded-lg px-3 py-1.5 text-sm" required />
          <select value={newSchool.board}
            onChange={(e) => setNewSchool({ ...newSchool, board: e.target.value })}
            className="border rounded-lg px-3 py-1.5 text-sm">
            <option>CBSE</option><option>ICSE</option><option>State</option><option>IB</option><option>Cambridge</option>
          </select>
          <input placeholder="City" value={newSchool.city}
            onChange={(e) => setNewSchool({ ...newSchool, city: e.target.value })}
            className="border rounded-lg px-3 py-1.5 text-sm" />
          <button className="bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-sm">Create</button>
        </form>
      </div>
    </div>
  );
}

function Column({ title, items, selectedId, onSelect, renderLabel }: {
  title: string; items: Node[]; selectedId?: string | null;
  onSelect: (n: Node) => void; renderLabel: (n: Node) => string;
}) {
  return (
    <div className="rounded-xl border bg-white overflow-hidden">
      <div className="px-4 py-2 border-b bg-gray-50 font-medium text-sm">{title}</div>
      <ul className="max-h-64 overflow-y-auto">
        {items.length === 0 && <li className="px-4 py-3 text-sm text-gray-400">No items yet</li>}
        {items.map((n) => (
          <li key={n.id}>
            <button
              onClick={() => onSelect(n)}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-emerald-50 ${
                selectedId === n.id ? "bg-emerald-100 font-medium" : ""
              }`}
            >
              {renderLabel(n)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
