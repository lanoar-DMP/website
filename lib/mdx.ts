import fs from "node:fs";
import path from "node:path";

import matter from "gray-matter";

interface PostMeta {
  title: string;
  date: string;
  description: string;
  tags: string[];
}

const BLOG_DIRECTORY = path.join(process.cwd(), "content", "blog");

export function getPostSlugs(): string[] {
  if (!fs.existsSync(BLOG_DIRECTORY)) {
    return [];
  }

  return fs
    .readdirSync(BLOG_DIRECTORY)
    .filter((fileName) => fileName.endsWith(".mdx"))
    .map((fileName) => fileName.replace(/\.mdx$/, ""));
}

export function getPostBySlug(slug: string): { meta: PostMeta; content: string } {
  const fullPath = path.join(BLOG_DIRECTORY, `${slug}.mdx`);
  const fileContents = fs.readFileSync(fullPath, "utf8");
  const { data, content } = matter(fileContents);

  const tags: string[] = Array.isArray(data.tags)
    ? data.tags.filter((t: unknown): t is string => typeof t === "string")
    : [];

  return {
    meta: {
      title: typeof data.title === "string" ? data.title : slug,
      date: typeof data.date === "string" ? data.date : "",
      description: typeof data.description === "string" ? data.description : "",
      tags,
    },
    content,
  };
}
