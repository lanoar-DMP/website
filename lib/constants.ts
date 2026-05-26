export const API_BASE_URLS = {
  macro: "/api/macro",
  markets: "/api/markets",
  card: "/api/card",
} as const;

export const REFRESH_INTERVALS = {
  fast: 15_000,
  standard: 60_000,
  slow: 300_000,
} as const;

export const TERMINAL_NAV_ITEMS = [
  {
    title: "Overview",
    href: "/terminal/overview",
  },
  {
    title: "Macro",
    href: "/terminal/macro",
  },
  {
    title: "Markets",
    href: "/terminal/markets",
  },
  {
    title: "Geopolitics",
    href: "/terminal/geopolitics",
  },
] as const;
