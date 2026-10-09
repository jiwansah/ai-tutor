"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { listSchools, listClasses } from "@/lib/teacherApi";
import { schoolSummary, schoolTrend, classSummary, triggerRollup } from "@/lib/analyticsApi";

export default function AnalyticsPage() {
  const [schools, setSchools] = useState<any[]>([]);
  const [schoolId, setSchoolId] = useState("");
  const [classes, setClasses] = useState<any[]>([]);
  const [classId, setClassId] = useState("");

  const [summary, setSummary] = useState<any>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [classData, setClassData] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);

  // Load schools
  useEffect(() => {
    listSchools()
      .then((rows) => {
        setSchools(rows);
        if (rows[0]) setSchoolId(rows[0].id);
      })
      .catch(() => toast.error("Failed to load schools"));
  }, []);

  // Load classes when school changes
  useEffect(() => {
    setClassId("");
    setClassData(null);
    if (!schoolId) { setClasses([]); return; }
    listClasses(schoolId)
      .then(setClasses)
      .catch(() => setClasses([]));
  }, [schoolId]);

  // School summary + trend
  useEffect(() => {
    if (!schoolId) return;
    setLoading(true);
    Promise.all([schoolSummary(schoolId, days), schoolTrend(schoolId, 14)])
      .then(([s, t]) => { setSummary(s); setTrend(t); })
      .catch((e) => toast.error(e?.response?.data?.detail || "Failed to load school analytics"))
      .finally(() => setLoading(false));
  }, [schoolId, days]);

  // Class drill-down
  useEffect(() => {
    if (!classId) { setClassData(null); return; }
    classSummary(classId, days)
      .then(setClassData)
      .catch((e) => toast.error(e?.response?.data?.detail || "Failed to load class analytics"));
  }, [classId, days]);

  async function handleRollup() {
    const today = new Date().toISOString().slice(0, 10);
    try {
      await triggerRollup(today);
      toast.success(`Rollup computed for ${today}`);
      if (schoolId) schoolTrend(schoolId, 14).then(setTrend);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Rollup failed");
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-gray-600 text-sm">
            Privacy-safe, aggregated metrics. No individual student data.
          </p>
        </div>
        <button
          onClick={handleRollup}
          className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-emerald-700"
        >
          Compute today's rollup
        </button>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={schoolId}
          onChange={(e) => setSchoolId(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm bg-white"
        >
          {schools.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        <select
          value={classId}
          onChange={(e) => setClassId(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value="">— All classes —</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>Class {c.grade}</option>
          ))}
        </select>

        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="border rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading && <div className="text-gray-400">Loading…</div>}

      {summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Active students" value={summary.active_students} />
            <Stat label="Questions asked" value={summary.questions_asked} />
            <Stat label="Correct rate" value={`${Math.round(summary.correct_rate * 100)}%`} />
            <Stat label="Verified rate" value={`${Math.round(summary.verified_rate * 100)}%`} />
          </div>

          {Object.keys(summary.mode_distribution || {}).length > 0 && (
            <div className="rounded-xl border bg-white p-5">
              <h2 className="font-semibold mb-3">Mode usage</h2>
              <div className="space-y-2">
                {Object.entries(summary.mode_distribution).map(([mode, count]: any) => {
                  const total = Object.values(summary.mode_distribution)
                    .reduce((a: any, b: any) => a + b, 0) as number;
                  const pct = total ? Math.round((count / total) * 100) : 0;
                  return (
                    <div key={mode} className="flex items-center gap-3 text-sm">
                      <div className="w-24 text-gray-700 capitalize">{mode}</div>
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="w-24 text-right text-gray-500">
                        {count} ({pct}%)
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {trend.length > 0 && (
        <div className="rounded-xl border bg-white p-5">
          <h2 className="font-semibold mb-3">Daily trend (last 14 days)</h2>
          <div className="space-y-1 text-sm">
            {trend.map((t) => (
              <div key={t.day} className="flex items-center gap-3">
                <div className="w-24 text-gray-500">{t.day}</div>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500"
                    style={{ width: `${Math.min(100, t.questions_asked)}%` }}
                  />
                </div>
                <div className="w-44 text-right text-gray-500">
                  {t.questions_asked} Q · {t.active_students} students
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {classData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border bg-white p-5">
            <h2 className="font-semibold mb-3">Top concepts</h2>
            {classData.top_concepts?.length === 0 && (
              <p className="text-sm text-gray-400">No data yet</p>
            )}
            <ul className="space-y-1 text-sm">
              {classData.top_concepts?.map((c: any, i: number) => (
                <li key={i} className="flex justify-between">
                  <span className="font-mono text-xs">{c.concept}</span>
                  <span className="text-gray-500">{c.count}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border bg-white p-5">
            <h2 className="font-semibold mb-3">Weakest concepts (k≥5)</h2>
            {classData.weak_concepts?.length === 0 && (
              <p className="text-sm text-gray-400">Not enough data yet</p>
            )}
            <ul className="space-y-1 text-sm">
              {classData.weak_concepts?.map((c: any, i: number) => (
                <li key={i} className="flex justify-between">
                  <span className="font-mono text-xs">{c.concept}</span>
                  <span className="text-red-600">
                    {Math.round(c.correct_rate * 100)}% · {c.attempts} attempts
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-xl border bg-white p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}
