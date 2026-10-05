"use client";
import { useEffect, useState } from "react";
import { myProgress } from "@/lib/api";

export default function ProgressPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    myProgress().then(setData).catch(() => {});
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Progress</h1>
      {!data ? (
        <p>Loading…</p>
      ) : (
        <div className="space-y-4">
          <h2 className="font-semibold">Weak areas</h2>
          {data.weak_areas?.length === 0 && <p className="text-gray-500">None yet — keep practicing!</p>}
          <ul className="space-y-2">
            {data.weak_areas?.map((w: any) => (
              <li key={w.concept} className="bg-white p-3 rounded-lg shadow-sm">
                <div className="flex justify-between">
                  <span>{w.concept}</span>
                  <span className="text-gray-500">{(w.mastery * 100).toFixed(0)}%</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
