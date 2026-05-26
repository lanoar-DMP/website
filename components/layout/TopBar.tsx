"use client";

import { UserButton } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

function formatPageTitle(pathname: string) {
  const segment = pathname.split("/").filter(Boolean).at(-1) ?? "overview";
  return segment.charAt(0).toUpperCase() + segment.slice(1);
}

function getUtcTime() {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "UTC",
    hour12: false,
  }).format(new Date());
}

export function TopBar() {
  const pathname = usePathname();
  const [utcTime, setUtcTime] = useState<string>(getUtcTime);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setUtcTime(getUtcTime());
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  return (
    <header className="flex h-16 items-center justify-between border-b border-terminal-border bg-terminal-bg px-6">
      <div className="flex items-center gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-terminal-muted">Workspace</p>
          <h1 className="text-xl font-semibold text-white">{formatPageTitle(pathname)}</h1>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Badge variant="secondary">UTC</Badge>
        <span className="font-mono text-sm text-zinc-200">{utcTime}</span>
        <Separator orientation="vertical" className="h-6" />
        <Badge variant="default">Connected</Badge>
        <UserButton
          appearance={{
            elements: {
              userButtonAvatarBox: "h-8 w-8",
            },
          }}
        />
      </div>
    </header>
  );
}
