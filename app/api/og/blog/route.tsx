import { ImageResponse } from "@vercel/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

const CARD_WIDTH = 1200;
const CARD_HEIGHT = 630;

function formatDate(date: string): string {
  if (!date) return "";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(date));
}

function clampText(text: string, maxChars: number): string {
  return text.length <= maxChars ? text : `${text.slice(0, maxChars - 3)}...`;
}

async function loadFonts(): Promise<
  Array<{ name: string; data: ArrayBuffer; style: "normal"; weight: 400 | 700 }>
> {
  const baseUrl = process.env.NEXT_PUBLIC_URL ?? "http://localhost:3000";
  const [regular, bold] = await Promise.all([
    fetch(`${baseUrl}/fonts/Inter-Regular.ttf`),
    fetch(`${baseUrl}/fonts/Inter-Bold.ttf`),
  ]);
  return [
    { name: "Inter", data: await regular.arrayBuffer(), style: "normal" as const, weight: 400 as const },
    { name: "Inter", data: await bold.arrayBuffer(), style: "normal" as const, weight: 700 as const },
  ];
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get("title") ?? "Holy Terminal";
  const slug = searchParams.get("slug") ?? "";
  const date = searchParams.get("date") ?? "";
  const tagsParam = searchParams.get("tags") ?? "";

  const tags = tagsParam ? tagsParam.split(",").filter(Boolean) : [];
  const fonts = await loadFonts();

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          width: "100%",
          height: "100%",
          background: "#080808",
          color: "#ffffff",
          fontFamily: "Inter",
          padding: "56px",
        }}
      >
        {/* Border container */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            height: "100%",
            border: "1px solid #222222",
            borderRadius: "16px",
            padding: "48px",
            background: "linear-gradient(135deg, #080808 0%, #0a0a1a 50%, #080808 100%)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Subtle grid overlay */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
              backgroundSize: "40px 40px",
            }}
          />

          {/* Top bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              position: "relative",
              zIndex: 1,
            }}
          >
            <div style={{ color: "#666666", fontSize: 14, letterSpacing: "0.28em" }}>
              HOLY TERMINAL
            </div>
            <div style={{ color: "#666666", fontSize: 16 }}>
              holyterminal.com{slug ? `/blog/${slug}` : ""}
            </div>
          </div>

          {/* Tags */}
          {tags.length > 0 && (
            <div
              style={{
                display: "flex",
                gap: 8,
                marginTop: 32,
                position: "relative",
                zIndex: 1,
              }}
            >
              {tags.slice(0, 4).map((tag) => (
                <div
                  key={tag}
                  style={{
                    display: "flex",
                    padding: "4px 14px",
                    borderRadius: 999,
                    fontSize: 13,
                    fontWeight: 500,
                    background: "rgba(255,255,255,0.06)",
                    color: "#999999",
                    border: "1px solid rgba(255,255,255,0.08)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  {tag}
                </div>
              ))}
            </div>
          )}

          {/* Title */}
          <div
            style={{
              display: "flex",
              flex: 1,
              alignItems: "center",
              position: "relative",
              zIndex: 1,
            }}
          >
            <div
              style={{
                fontSize: 48,
                fontWeight: 700,
                lineHeight: 1.15,
                color: "#ffffff",
                maxWidth: 800,
                letterSpacing: "-0.02em",
              }}
            >
              {clampText(title, 80)}
            </div>
          </div>

          {/* Bottom bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              position: "relative",
              zIndex: 1,
              borderTop: "1px solid rgba(255,255,255,0.06)",
              paddingTop: 24,
            }}
          >
            <div style={{ display: "flex", gap: 18, color: "#666666", fontSize: 15 }}>
              {date && <span>{formatDate(date)}</span>}
            </div>
            <div style={{ display: "flex", color: "#444444", fontSize: 13, letterSpacing: "0.15em" }}>
              BUILD IN PUBLIC
            </div>
          </div>
        </div>
      </div>
    ),
    {
      width: CARD_WIDTH,
      height: CARD_HEIGHT,
      fonts,
      headers: {
        "Cache-Control": "public, s-maxage=604800, stale-while-revalidate=86400",
      },
    },
  );
}