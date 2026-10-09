"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/store";
import { MobileMenu, type NavItem } from "@/components/nav/MobileMenu";

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/tutor",     label: "Tutor" },
  { href: "/progress",  label: "Progress" },
  { href: "/profile",   label: "Profile" },
];

export default function TutorLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [checked, setChecked] = useState(false);

  // Keep the app shell aligned with the actually visible viewport on mobile.
  // This accounts for browser address bars and the on-screen keyboard.
  useEffect(() => {
    const updateAppHeight = () => {
      const height = window.visualViewport?.height ?? window.innerHeight;
      document.documentElement.style.setProperty("--app-height", `${height}px`);
    };

    updateAppHeight();
    window.addEventListener("resize", updateAppHeight);
    window.visualViewport?.addEventListener("resize", updateAppHeight);
    window.visualViewport?.addEventListener("scroll", updateAppHeight);

    return () => {
      window.removeEventListener("resize", updateAppHeight);
      window.visualViewport?.removeEventListener("resize", updateAppHeight);
      window.visualViewport?.removeEventListener("scroll", updateAppHeight);
      document.documentElement.style.removeProperty("--app-height");
    };
  }, []);

  useEffect(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) { router.replace("/login"); return; }
    if (user) {
      if (user.role === "teacher" || user.role === "admin") {
        router.replace("/teacher");
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
  const isChat = pathname === "/tutor";

  return (
    <div className="app-shell flex flex-col overflow-hidden bg-gray-50">
      <MobileMenu
        items={NAV}
        brandHref="/tutor"
        brandLabel="AI Tutor"
        brandColor="text-indigo-600"
        userName={user?.full_name}
        onLogout={handleLogout}
      />

      <header className="hidden md:flex h-16 flex-shrink-0 border-b bg-white px-6 items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/tutor" className="font-bold text-lg text-indigo-600">AI Tutor</Link>
          <nav className="flex gap-1">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  pathname === n.href ? "bg-indigo-50 text-indigo-700" : "text-gray-700 hover:bg-gray-100"
                }`}>
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/profile" className="text-sm text-gray-600 hover:text-indigo-600">
            {user?.full_name}
          </Link>
          <button onClick={handleLogout} className="text-sm text-red-600 hover:underline">
            Logout
          </button>
        </div>
      </header>

      {/* flex-1 min-h-0 makes this child fill remaining space and disallow overflow */}
      <main className={`flex-1 min-h-0 ${isChat ? "overflow-hidden" : "overflow-y-auto"}`}>
        {children}
      </main>
    </div>
  );
}
