"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowLeft, Check, Loader2, Save, X } from "lucide-react";
import {
  getJob, getPreview, updateParsed, approveJob,
  type IngestJob, type ParsedData, type ParsedChapter, type ParsedSection,
} from "@/lib/ingestApi";

export default function IngestJobDetail() {
  const params = useParams<{ jobId: string }>();
  const router = useRouter();
  const jobId = params.jobId;

  const [job, setJob] = useState<IngestJob | null>(null);
  const [parsed, setParsed] = useState<ParsedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    load();
  }, [jobId]);

  // Poll while in-progress
  useEffect(() => {
    if (!job) return;
    if (job.status === "pending" || job.status === "parsing" || job.status === "publishing") {
      const t = setInterval(load, 2500);
      return () => clearInterval(t);
    }
  }, [job?.status]);

  async function load() {
    try {
      const j = await getJob(jobId);
      setJob(j);
      if (j.status === "preview_ready" || j.status === "approved") {
        const p = await getPreview(jobId);
        setParsed(p);
      }
      // During "publishing", keep showing the last known preview — don't refetch
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load job");
    } finally {
      setLoading(false);
    }
  }

  function updateChapterTitle(idx: number, title: string) {
    if (!parsed) return;
    const next = { ...parsed, chapters: [...parsed.chapters] };
    next.chapters[idx] = { ...next.chapters[idx], title };
    setParsed(next);
  }

  function updateSectionTitle(cIdx: number, sIdx: number, title: string) {
    if (!parsed) return;
    const chapters = [...parsed.chapters];
    const sections = [...chapters[cIdx].sections];
    sections[sIdx] = { ...sections[sIdx], title };
    chapters[cIdx] = { ...chapters[cIdx], sections };
    setParsed({ ...parsed, chapters });
  }

  function deleteChapter(idx: number) {
    if (!parsed) return;
    if (!confirm("Remove this chapter? Its sections won't be ingested.")) return;
    const chapters = parsed.chapters.filter((_, i) => i !== idx);
    setParsed({ ...parsed, chapters });
  }

  function deleteSection(cIdx: number, sIdx: number) {
    if (!parsed) return;
    const chapters = [...parsed.chapters];
    const sections = chapters[cIdx].sections.filter((_, i) => i !== sIdx);
    chapters[cIdx] = { ...chapters[cIdx], sections };
    setParsed({ ...parsed, chapters });
  }

  async function handleSave() {
    if (!parsed) return;
    setSaving(true);
    try {
      await updateParsed(jobId, parsed);
      toast.success("Changes saved");
    } catch {
      toast.error("Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove() {
    if (!parsed) return;
    if (!confirm("Publish this content? Chapters, sections, and chunks will be added to the tutor.")) return;
    setApproving(true);
    try {
      await updateParsed(jobId, parsed);   // save latest edits first
      await approveJob(jobId);
      toast.success("Publishing started");
      await load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Approve failed");
    } finally {
      setApproving(false);
    }
  }

  if (loading) return <div className="p-6 text-gray-400">Loading…</div>;
  if (!job) return <div className="p-6 text-red-600">Job not found</div>;

  const isPreview = job.status === "preview_ready";
  const isApproved = job.status === "approved";
  const isWorking = job.status === "pending" || job.status === "parsing" || job.status === "publishing";
  const isFailed = job.status === "failed";

  return (
    <div className="space-y-6">
      <button onClick={() => router.push("/teacher/ingest")}
        className="text-sm text-emerald-600 hover:underline flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> Back to uploads
      </button>

      <div>
        <h1 className="text-2xl font-bold">{job.filename}</h1>
        <p className="text-gray-600 text-sm mt-1">
          {job.page_count > 0 && <>{job.page_count} pages · </>}
          {job.file_size_kb} KB · status: <b>{job.status}</b>
        </p>
      </div>

      {/* Status panel */}
      {isWorking && (
        <div className="rounded-xl border bg-white p-5">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
            <span className="font-medium">
              {job.status === "parsing" ? "Parsing PDF…" :
               job.status === "publishing" ? "Publishing (embedding chunks)…" :
               "Queued"}
            </span>
          </div>
          <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 transition-all"
              style={{ width: `${job.progress}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-2">{job.progress}%</p>
        </div>
      )}

      {isFailed && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <div className="font-medium text-red-800">Parse failed</div>
          <div className="text-sm text-red-700 mt-1">{job.error_message}</div>
        </div>
      )}

      {/* Parsed structure */}
      {parsed && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-gray-600">
              {parsed.chapters.length} chapters ·{" "}
              {parsed.chapters.reduce((n, c) => n + c.sections.length, 0)} sections ·{" "}
              {parsed.chapters.reduce((n, c) => n + c.sections.reduce((m, s) => m + s.chunks.length, 0), 0)} chunks
            </div>

            {isPreview && (
              <div className="flex gap-2">
                <button onClick={handleSave} disabled={saving}
                  className="bg-gray-100 text-gray-800 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save edits
                </button>
                <button onClick={handleApprove} disabled={approving}
                  className="bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-1">
                  {approving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Approve & Publish
                </button>
              </div>
            )}

            {isApproved && (
              <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-green-50 text-green-700 font-medium">
                <Check className="w-4 h-4" /> Published
              </span>
            )}
          </div>

          <div className="space-y-4">
            {parsed.chapters.map((ch, cIdx) => (
              <ChapterBlock
                key={cIdx}
                chapter={ch}
                editable={isPreview}
                expanded={!!expanded[`c${cIdx}`]}
                onToggle={() => setExpanded((e) => ({ ...e, [`c${cIdx}`]: !e[`c${cIdx}`] }))}
                onChangeTitle={(t) => updateChapterTitle(cIdx, t)}
                onDelete={() => deleteChapter(cIdx)}
                onChangeSectionTitle={(sIdx, t) => updateSectionTitle(cIdx, sIdx, t)}
                onDeleteSection={(sIdx) => deleteSection(cIdx, sIdx)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}


function ChapterBlock({
  chapter, editable, expanded, onToggle, onChangeTitle, onDelete,
  onChangeSectionTitle, onDeleteSection,
}: {
  chapter: ParsedChapter;
  editable: boolean;
  expanded: boolean;
  onToggle: () => void;
  onChangeTitle: (t: string) => void;
  onDelete: () => void;
  onChangeSectionTitle: (sIdx: number, t: string) => void;
  onDeleteSection: (sIdx: number) => void;
}) {
  const totalChunks = chapter.sections.reduce((n, s) => n + s.chunks.length, 0);

  return (
    <div className="rounded-xl border bg-white overflow-hidden">
      <div className="px-4 py-3 flex flex-wrap items-center gap-3">
        <button onClick={onToggle}
          className="text-gray-500 hover:text-gray-800 text-sm">
          {expanded ? "▼" : "▶"}
        </button>

        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-emerald-50 text-emerald-700 text-sm font-semibold">
          {chapter.number}
        </span>

        {editable ? (
          <input
            value={chapter.title}
            onChange={(e) => onChangeTitle(e.target.value)}
            placeholder="Chapter title"
            className="flex-1 border rounded-lg px-3 py-1.5 text-sm"
          />
        ) : (
          <span className="flex-1 font-medium">{chapter.title || "(untitled)"}</span>
        )}

        <span className="text-xs text-gray-500">
          pp. {chapter.start_page}–{chapter.end_page} · {chapter.sections.length} sec · {totalChunks} chunks
        </span>

        {editable && (
          <button onClick={onDelete}
            className="text-red-500 hover:text-red-700 p-1"
            aria-label="Delete chapter">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {expanded && (
        <div className="border-t bg-gray-50 divide-y">
          {chapter.sections.length === 0 && (
            <div className="px-4 py-3 text-sm text-gray-400">No sections detected</div>
          )}
          {chapter.sections.map((sec, sIdx) => (
            <div key={sIdx} className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-gray-600 min-w-[36px]">
                  {sec.number}
                </span>

                {editable ? (
                  <input
                    value={sec.title}
                    onChange={(e) => onChangeSectionTitle(sIdx, e.target.value)}
                    placeholder="Section title"
                    className="flex-1 border rounded-lg px-2 py-1 text-sm"
                  />
                ) : (
                  <span className="flex-1 text-sm">{sec.title}</span>
                )}

                <span className="text-xs text-gray-500">
                  pp. {sec.start_page}–{sec.end_page} · {sec.chunks.length} chunks
                </span>

                {editable && (
                  <button onClick={() => onDeleteSection(sIdx)}
                    className="text-red-500 hover:text-red-700 p-1"
                    aria-label="Delete section">
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {sec.chunks.length > 0 && (
                <details className="mt-2 text-xs text-gray-600">
                  <summary className="cursor-pointer text-emerald-700 hover:text-emerald-900">
                    Preview chunks
                  </summary>
                  <ul className="mt-2 space-y-2">
                    {sec.chunks.map((c, i) => (
                      <li key={i} className="rounded-md bg-white border px-3 py-2">
                        <div className="text-[10px] uppercase tracking-wide text-gray-400 mb-1">
                          p. {c.page}
                        </div>
                        <div className="whitespace-pre-wrap">{c.text}</div>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
