import { Circle } from "lucide-react";
import DashboardGrid from "@/components/dashboard/DashboardGrid";
import TimeDisplay from "@/components/dashboard/TimeDisplay";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Top Bar */}
      <header className="sticky top-0 z-50 border-b border-[#1a1a1a] bg-[#0a0a0a]/95 backdrop-blur">
        <div className="mx-auto flex h-10 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm font-bold tracking-[0.2em] text-terminal-green">
              HOLY TERMINAL
            </span>
            <span className="hidden font-mono text-[10px] text-zinc-700 md:inline-block">
              v0.1.0
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* System status indicator */}
            <div className="flex items-center gap-1.5">
              <Circle className="h-2 w-2 fill-terminal-green text-terminal-green" />
              <span className="font-mono text-[10px] text-zinc-500">LIVE</span>
            </div>

            {/* Current time (UTC) */}
            <TimeDisplay />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-4">
        <DashboardGrid />
      </main>

      {/* Status bar at bottom */}
      <footer className="fixed bottom-0 left-0 right-0 border-t border-[#1a1a1a] bg-[#0a0a0a]">
        <div className="mx-auto flex h-6 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] text-zinc-700">
              HOLYTERMINAL://dashboard
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-zinc-700">
              DATA REFRESH: 30s
            </span>
            <span className="font-mono text-[10px] text-zinc-700">|</span>
            <span className="font-mono text-[10px] text-zinc-700">
              CONNECTED
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
