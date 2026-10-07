"use client";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

interface Prereq {
  key: string;
  name: string;
  mastery: number;
  status: "weak" | "developing" | "ok";
  primary_section_id: string | null;
}

interface Diagnostic {
  concept_key?: string | null;
  mastery?: number;
  prerequisites?: Prereq[];
  recommendation?: string;
  recommended_prerequisite?: string | null;
}

export function DiagnosticBanner({ diagnostic }: { diagnostic?: Diagnostic }) {
  if (!diagnostic?.concept_key) return null;

  const rec = diagnostic.recommendation;
  const prereqs = diagnostic.prerequisites ?? [];

  if (rec === "review_prerequisite") {
    const weakName =
      prereqs.find((p) => p.key === diagnostic.recommended_prerequisite)?.name ??
      diagnostic.recommended_prerequisite;
    return (
      <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
        <div>
          <div className="font-medium">Prerequisite gap detected</div>
          <div className="text-amber-800">
            You haven't fully mastered <strong>{weakName}</strong> yet. The tutor will briefly
            review it before continuing.
          </div>
        </div>
      </div>
    );
  }

  if (rec === "challenge") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
        <CheckCircle2 className="w-4 h-4" />
        You're ready — the tutor will move faster.
      </div>
    );
  }

  if (rec === "scaffold") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
        <Info className="w-4 h-4" />
        New concept — the tutor will guide you step by step.
      </div>
    );
  }

  return null;
}
