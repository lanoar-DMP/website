import Link from "next/link";

import { getPostBySlug, getPostSlugs } from "@/lib/mdx";

function formatDate(date: string): string {
  if (!date) {
    return "";
  }

  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(date));
}

const TAG_COLORS: Record<string, string> = {
  ai: "bg-emerald-900/40 text-emerald-300",
  diy: "bg-blue-900/40 text-blue-300",
  tutorial: "bg-purple-900/40 text-purple-300",
  python: "bg-amber-900/40 text-amber-300",
  nextjs: "bg-zinc-700/40 text-zinc-300",
  crypto: "bg-orange-900/40 text-orange-300",
  defi: "bg-teal-900/40 text-teal-300",
  security: "bg-red-900/40 text-red-300",
};

function TagBadge({ tag }: { tag: string }) {
  const color = TAG_COLORS[tag] ?? "bg-terminal-muted/20 text-terminal-muted";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${color}`}>
      {tag}
    </span>
  );
}

export default function BlogIndexPage() {
  const posts = getPostSlugs()
    .map((slug) => ({
      slug,
      ...getPostBySlug(slug),
    }))
    .sort((left, right) => right.meta.date.localeCompare(left.meta.date));

  return (
    <main className="min-h-screen bg-terminal-bg px-6 py-16 text-white">
      <div className="mx-auto max-w-4xl">
        <p className="text-xs uppercase tracking-[0.28em] text-terminal-muted">Holy Terminal Journal</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight">Research and market structure notes</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-400 max-w-2xl">
          Building quant tools, AI agents, and trading dashboards from first principles. 
          All the code is open-source and runs on a Mac Mini.
        </p>
        <div className="mt-10 space-y-5">
          {posts.length === 0 && (
            <p className="text-terminal-muted">No posts yet. Coming soon.</p>
          )}
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="block rounded-lg border border-terminal-border bg-terminal-card p-6 transition-colors hover:border-terminal-blue/60"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.18em] text-terminal-muted">
                  {formatDate(post.meta.date)}
                </p>
                <div className="flex gap-1.5">
                  {post.meta.tags.map((tag) => (
                    <TagBadge key={tag} tag={tag} />
                  ))}
                </div>
              </div>
              <h2 className="mt-3 text-2xl font-semibold text-white">{post.meta.title}</h2>
              <p className="mt-2 text-sm leading-6 text-zinc-300">{post.meta.description}</p>
            </Link>
          ))}
        </div>

        {/* Newsletter CTA */}
        <div className="mt-16 rounded-lg border border-terminal-border bg-terminal-card p-8">
          <h3 className="text-lg font-semibold text-white">Get new posts in your inbox</h3>
          <p className="mt-2 text-sm text-zinc-400">
            New research, quant models, and DIY trading tools. No spam.
          </p>
          <form
            action="https://macrobombastic.substack.com/subscribe"
            method="get"
            target="_blank"
            className="mt-4 flex gap-3"
          >
            <input
              type="email"
              name="email"
              placeholder="your@email.com"
              required
              className="flex-1 rounded-md border border-terminal-border bg-terminal-bg px-4 py-2.5 text-sm text-white placeholder-zinc-500 outline-none focus:border-terminal-blue/60"
            />
            <button
              type="submit"
              className="rounded-md bg-white px-5 py-2.5 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
            >
              Subscribe
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
