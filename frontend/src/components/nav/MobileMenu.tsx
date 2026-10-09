"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
}

interface Props {
  items: NavItem[];
  brandHref: string;
  brandLabel: string;
  brandColor?: string;
  userName?: string;
  onLogout: () => void;
}

export function MobileMenu({
  items,
  brandHref,
  brandLabel,
  brandColor = "text-indigo-600",
  userName,
  onLogout,
}: Props) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      {/* Plain flex-item header — no sticky, no fixed, no safe-top */}
      <header className="md:hidden flex-shrink-0 h-14 bg-white border-b flex items-center justify-between px-4">
        <Link href={brandHref} className={`font-bold text-lg ${brandColor}`}>
          {brandLabel}
        </Link>
        <button
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          className="p-2 -mr-2 rounded-lg hover:bg-gray-100"
        >
          <Menu className="w-6 h-6" />
        </button>
      </header>

      {open && (
        <div
          className="md:hidden fixed inset-0 z-50 bg-black/40"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        className={`md:hidden fixed top-0 right-0 bottom-0 z-50 w-72 max-w-[85vw] bg-white shadow-xl transform transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between h-14 px-4 border-b">
          <span className="font-semibold">Menu</span>
          <button
            onClick={() => setOpen(false)}
            aria-label="Close menu"
            className="p-2 -mr-2 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <nav className="p-2">
          {items.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block px-4 py-3 rounded-lg text-base font-medium ${
                  active
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 border-t p-4 space-y-3 safe-bottom">
          {userName && (
            <div className="text-sm text-gray-600 truncate">Signed in as <b>{userName}</b></div>
          )}
          <button
            onClick={onLogout}
            className="w-full text-center rounded-lg border border-red-200 text-red-600 py-2.5 font-medium hover:bg-red-50"
          >
            Logout
          </button>
        </div>
      </aside>
    </>
  );
}
