"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/store";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/tutor", label: "Tutor" },
  { href: "/progress", label: "Progress" },
];

export default function TutorLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) router.push("/login");
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="h-16 border-b bg-white px-6 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="font-bold text-lg text-indigo-600">
            AI Tutor
          </Link>
          <nav className="flex gap-1">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  pathname === n.href
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user?.full_name || "Student"}</span>
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="text-sm text-red-600 hover:underline"
          >
            Logout
          </button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
