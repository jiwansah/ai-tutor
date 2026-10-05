"use client";

const MODES = [
  { id: "teacher",  label: "👨‍🏫 Teacher" },
  { id: "socratic", label: "🧠 Socratic" },
  { id: "hint",     label: "💡 Hint" },
  { id: "practice", label: "🧩 Practice" },
  { id: "revision", label: "🎯 Revision" },
  { id: "doubt",    label: "🔍 Doubt" },
  { id: "exam",     label: "📝 Exam" },
  { id: "quiz",     label: "⚡ Quiz" },
];

export function ModeSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm bg-white"
    >
      {MODES.map((m) => (
        <option key={m.id} value={m.id}>
          {m.label}
        </option>
      ))}
    </select>
  );
}
