"use client";

import { useEffect, useState } from "react";

interface ShareButtonProps {
  type: "macro" | "market";
  id: string;
  label: string;
  isPro: boolean;
}

function buildCardUrl(type: "macro" | "market", id: string, isPro: boolean): string {
  const params = new URLSearchParams({ type });

  if (type === "macro") {
    params.set("seriesId", id);
  } else {
    params.set("marketId", id);
  }

  if (isPro) {
    params.set("pro", "1");
  }

  return `/api/card?${params.toString()}`;
}

export function ShareButton({ type, id, label, isPro }: ShareButtonProps) {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setToastMessage(null);
    }, 2400);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [toastMessage]);

  async function handleShare(): Promise<void> {
    const cardUrl = buildCardUrl(type, id, isPro);
    const clipboard = navigator.clipboard;

    if (typeof window.ClipboardItem === "undefined" || typeof clipboard?.write !== "function") {
      window.open(cardUrl, "_blank", "noopener,noreferrer");
      return;
    }

    try {
      const response = await fetch(cardUrl);

      if (!response.ok) {
        throw new Error(`Card request failed: ${response.status}`);
      }

      const blob = await response.blob();
      await clipboard.write([new window.ClipboardItem({ [blob.type]: blob })]);
      setToastMessage("Card copied! Paste to X.");
    } catch {
      window.open(cardUrl, "_blank", "noopener,noreferrer");
      setToastMessage(`Opened ${label} card in a new tab.`);
    }
  }

  return (
    <div className="relative flex items-center justify-end">
      <button
        type="button"
        onClick={handleShare}
        className="text-sm font-medium text-zinc-300 transition-colors hover:text-white"
      >
        Share →
      </button>
      {toastMessage ? (
        <div className="absolute right-0 top-full z-20 mt-2 min-w-48 rounded-md border border-terminal-border bg-terminal-bg px-3 py-2 text-xs text-white shadow-lg">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
