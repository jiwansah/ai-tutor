"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/store";
import { MobileMenu, type NavItem } from "@/components/nav/MobileMenu";

const NAV: NavItem[] = [
  { href: "/teacher",             label: "Dashboard" },
  { href: "/teacher/curriculum",  label: "Curriculum" },
  { href: "/teacher/ingest",      label: "Upload" },
  { href: "/teacher/concepts",    label: "Concepts" },
  { href: "/teacher/graph",       label: "Graph" },
  { href: "/teacher/analytics",   label: "Analytics" },
  { href: "/teacher/profile",     label: "Profile" },
];

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) { router.replace("/login"); return; }
    if (user) {
      if (user.role !== "teacher" && user.role !== "admin") {
        router.replace("/tutor");
        return;
      }
      setChecked(true);
    }
  }, [user, router]);

  if (!checked) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        Loading…
      </div>
    );
  }

  const handleLogout = () => { logout(); router.push("/login"); };

  return (
    <div className="app-shell flex flex-col bg-gray-50">
      <MobileMenu
        items={NAV}
        brandHref="/teacher"
        brandLabel="AI Tutor · Teacher"
        brandColor="text-emerald-700"
        userName={user?.full_name}
        onLogout={handleLogout}
      />

      <header className="hidden md:flex h-16 flex-shrink-0 border-b bg-white px-6 items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/teacher" className="font-bold text-lg text-emerald-700">
            AI Tutor · Teacher
          </Link>
          <nav className="flex gap-1 flex-wrap">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  pathname === n.href
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/teacher/profile" className="text-sm text-gray-600 hover:text-emerald-600">
            {user?.full_name}
          </Link>
          <button onClick={handleLogout} className="text-sm text-red-600 hover:underline">
            Logout
          </button>
        </div>
      </header>

      {/* Other pages scroll inside main */}
      <main className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-4 sm:p-6">{children}</div>
      </main>
    </div>
  );
}
