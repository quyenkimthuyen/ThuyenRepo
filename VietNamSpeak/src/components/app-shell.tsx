import Link from "next/link";
import type { ReactNode } from "react";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/learn/school", label: "Word" },
  { href: "/ipa", label: "IPA Center" },
  { href: "/rules", label: "Rules" },
  { href: "/game", label: "Adventure" },
  { href: "/daily", label: "Daily" }
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-4 sm:px-6 lg:px-8">
      <header className="sticky top-0 z-20 mb-6 rounded-3xl border border-[var(--border)] bg-[var(--card)]/85 p-3 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="text-2xl font-black tracking-tight text-blue-600 dark:text-blue-300">
            VietNamSpeak
          </Link>
          <nav className="flex gap-2 overflow-x-auto pb-1 sm:pb-0" aria-label="Primary navigation">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="whitespace-nowrap rounded-full px-3 py-2 text-sm font-bold text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
