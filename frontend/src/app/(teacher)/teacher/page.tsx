"use client";
import Link from "next/link";
import { BookOpen, Network, Upload, Users } from "lucide-react";

export default function TeacherDashboard() {
  const cards = [
    { href: "/teacher/curriculum", icon: BookOpen, title: "Curriculum",
      desc: "Create schools, classes, subjects, books, chapters, and sections.",
      color: "bg-emerald-50 text-emerald-700" },
    { href: "/teacher/curriculum", icon: Upload, title: "Ingest Content",
      desc: "Paste or upload textbook content. Auto-embedded and searchable.",
      color: "bg-blue-50 text-blue-700" },
    { href: "/teacher/concepts", icon: Network, title: "Concepts",
      desc: "Define learning objectives, prerequisites, and common misconceptions.",
      color: "bg-purple-50 text-purple-700" },
    { href: "/teacher/graph", icon: Users, title: "Concept Graph",
      desc: "Visual map of prerequisite chains. Spot gaps at a glance.",
      color: "bg-amber-50 text-amber-700" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Teacher Dashboard</h1>
        <p className="text-gray-600 mt-1">Build and manage the AI Tutor curriculum.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cards.map((c) => (
          <Link
            key={c.title}
            href={c.href}
            className="block rounded-xl border bg-white p-5 hover:border-emerald-300 hover:shadow-sm transition"
          >
            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg ${c.color}`}>
              <c.icon className="w-4 h-4" />
              <span className="text-sm font-medium">{c.title}</span>
            </div>
            <p className="text-sm text-gray-600 mt-3">{c.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
