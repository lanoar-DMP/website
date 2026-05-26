"use client";

import { useState } from "react";

export function UpgradeButton() {
  const [isLoading, setIsLoading] = useState<boolean>(false);

  async function handleUpgrade(): Promise<void> {
    setIsLoading(true);

    try {
      const response = await fetch("/api/stripe/checkout", {
        method: "POST",
      });

      const payload = (await response.json()) as { url?: string };

      if (!payload.url) {
        throw new Error("Missing checkout URL.");
      }

      window.location.href = payload.url;
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleUpgrade}
      disabled={isLoading}
      className="rounded-md border border-terminal-green/40 bg-terminal-green/10 px-4 py-2 text-sm font-medium text-terminal-green transition-colors hover:bg-terminal-green/20 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {isLoading ? "Redirecting..." : "Upgrade to Pro"}
    </button>
  );
}
