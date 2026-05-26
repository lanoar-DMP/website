import { currentUser } from "@clerk/nextjs/server";

function isUserPlan(value: unknown): value is "free" | "pro" {
  return value === "free" || value === "pro";
}

export async function getUserPlan(): Promise<"free" | "pro"> {
  const user = await currentUser();
  const plan = user?.publicMetadata?.plan;

  return isUserPlan(plan) ? plan : "free";
}
