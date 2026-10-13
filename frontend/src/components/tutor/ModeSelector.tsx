"use client";

const MODES = [
  { id: "teacher",  label: "Teacher" },
  { id: "exam",     label: "Exam" },
  { id: "quiz",     label: "Quiz" },
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
      aria-label="Teaching mode"
      className="rounded-lg border border-gray-300 px-2.5 py-2 text-sm bg-white min-h-[40px] min-w-[110px]"
    >
      {MODES.map((m) => (
        <option key={m.id} value={m.id}>
          {m.label}
        </option>
      ))}
    </select>
  );
}
