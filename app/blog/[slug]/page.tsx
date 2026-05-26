import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";

import { MacroChart } from "@/components/mdx/MacroChart";
import { getPostBySlug, getPostSlugs } from "@/lib/mdx";

interface BlogPostPageProps {
  params: {
    slug: string;
  };
}

function formatDate(date: string): string {
  if (!date) {
    return "";
  }

  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(date));
}

function formatShortDate(date: string): string {
  if (!date) return "";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(date));
}

export function generateStaticParams(): Array<{ slug: string }> {
  return getPostSlugs().map((slug) => ({ slug }));
}

export function generateMetadata({ params }: BlogPostPageProps): Metadata {
  if (!getPostSlugs().includes(params.slug)) return {};

  const { meta } = getPostBySlug(params.slug);
  const baseUrl = process.env.NEXT_PUBLIC_URL ?? "https://holyterminal.com";

  // Build OG image URL with blog params
  const ogUrl = new URL(`${baseUrl}/api/og/blog`);
  ogUrl.searchParams.set("title", meta.title);
  ogUrl.searchParams.set("slug", params.slug);
  ogUrl.searchParams.set("date", meta.date);
  if (meta.tags.length > 0) {
    ogUrl.searchParams.set("tags", meta.tags.join(","));
  }

  return {
    title: `${meta.title} — Holy Terminal`,
    description: meta.description,
    openGraph: {
      title: meta.title,
      description: meta.description,
      type: "article",
      publishedTime: meta.date,
      url: `${baseUrl}/blog/${params.slug}`,
      images: [{ url: ogUrl.toString(), width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      title: meta.title,
      description: meta.description,
      images: [ogUrl.toString()],
      site: "@macrobombastic",
      creator: "@macrobombastic",
    },
  };
}

function TweetShareButton({ slug, title }: { slug: string; title: string }) {
  const baseUrl = process.env.NEXT_PUBLIC_URL ?? "https://holyterminal.com";
  const articleUrl = `${baseUrl}/blog/${slug}`;
  const tweetText = encodeURIComponent(
    `${title}\n\nFull article at Holy Terminal ↓`,
  );
  const shareUrl = `https://twitter.com/intent/tweet?text=${tweetText}&url=${encodeURIComponent(articleUrl)}&via=macrobombastic`;

  return (
    <a
      href={shareUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 rounded-md border border-terminal-border bg-terminal-card px-4 py-2 text-sm text-white transition-colors hover:border-terminal-blue/60"
    >
      <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
      Share on X
    </a>
  );
}

export default function BlogPostPage({ params }: BlogPostPageProps) {
  if (!getPostSlugs().includes(params.slug)) {
    notFound();
  }

  const { meta, content } = getPostBySlug(params.slug);

  return (
    <main className="min-h-screen bg-terminal-bg px-6 py-16 text-white">
      <article className="prose prose-invert mx-auto max-w-3xl">
        <p className="text-xs uppercase tracking-[0.24em] text-terminal-muted">{formatDate(meta.date)}</p>
        {meta.tags.length > 0 && (
          <div className="mt-3 flex gap-1.5">
            {meta.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block rounded-full bg-zinc-800 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-zinc-400"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white">{meta.title}</h1>
        <p className="mt-4 text-lg text-zinc-300">{meta.description}</p>
        <div className="mt-10 leading-7 text-zinc-200">
          <MDXRemote source={content} components={{ MacroChart }} />
        </div>

        {/* Footer */}
        <div className="mt-16 border-t border-terminal-border pt-8">
          <div className="flex items-center justify-between">
            <p className="text-xs text-terminal-muted">
              Published {formatShortDate(meta.date)} — Holy Terminal Research
            </p>
            <TweetShareButton slug={params.slug} title={meta.title} />
          </div>
        </div>
      </article>
    </main>
  );
}
