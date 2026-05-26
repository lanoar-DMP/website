"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { TERMINAL_NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-terminal-border bg-terminal-card">
      <div className="flex items-center justify-between px-5 py-4">
        <Link href="/terminal/overview" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-terminal-border bg-terminal-bg text-sm font-semibold tracking-[0.3em] text-terminal-green">
            HT
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-white">Holy Terminal</p>
            <p className="text-xs text-terminal-muted">Institutional workspace</p>
          </div>
        </Link>
        <Badge variant="positive" className="uppercase tracking-[0.2em]">
          Live
        </Badge>
      </div>

      <Separator />

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        {TERMINAL_NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-md border border-transparent px-3 py-2 text-sm font-medium text-zinc-400 transition-colors hover:border-terminal-border hover:bg-terminal-bg hover:text-white",
                isActive && "border-terminal-border bg-terminal-bg text-white",
              )}
            >
              {item.title}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
