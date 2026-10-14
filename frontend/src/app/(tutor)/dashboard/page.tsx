"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, TrendingUp, ArrowRight, Loader2 } from "lucide-react";
import { myProgress } from "@/lib/api";

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    myProgress()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const all = data?.all ?? [];
  const weak = data?.weak_areas ?? [];

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-600 text-sm mt-1">
          Welcome back. Here's your current learning snapshot.
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading…
        </div>
      )}

      {!loading && all.length === 0 && (
        <div className="rounded-xl border bg-white p-6 text-center space-y-3">
          <BookOpen className="w-8 h-8 text-indigo-500 mx-auto" />
          <p className="font-medium">No progress yet</p>
          <p className="text-sm text-gray-500">
            Ask your first question, or try a quiz to start tracking your mastery.
          </p>
          <Link
            href="/tutor"
            className="inline-flex items-center gap-1 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
          >
            Open Tutor <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {!loading && all.length > 0 && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Concepts tracked" value={all.length} />
            <Stat label="Weak areas" value={weak.length} />
            <Stat
              label="Avg mastery"
              value={`${Math.round((all.reduce((s: number, a: any) => s + a.mastery, 0) / all.length) * 100)}%`}
            />
            <Stat
              label="Total attempts"
              value={all.reduce((s: number, a: any) => s + a.attempts, 0)}
            />
          </div>

          {weak.length > 0 && (
            <div className="rounded-xl border bg-white">
              <div className="px-5 py-3 border-b bg-gray-50 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-600" />
                <span className="font-medium text-sm">Weak areas to focus on</span>
              </div>
              <ul className="divide-y">
                {weak.slice(0, 5).map((w: any) => (
                  <li key={w.concept_key ?? w.concept} className="px-5 py-3 flex items-center justify-between text-sm">
                    <span className="font-mono text-xs text-gray-600 truncate">
                      {w.concept}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-500">
                        {Math.round(w.mastery * 100)}% · {w.attempts} attempts
                      </span>
                      <Link
                        href="/tutor"
                        className="text-emerald-600 hover:underline text-xs"
                      >
                        Practice →
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Link
            href="/tutor"
            className="inline-flex items-center gap-1 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
          >
            Continue learning <ArrowRight className="w-4 h-4" />
          </Link>
        </>
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