import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

import { getStripe } from "@/lib/stripe";

function getBaseUrl(request: Request): string {
  return process.env.NEXT_PUBLIC_URL ?? new URL(request.url).origin;
}

export async function POST(request: Request): Promise<Response> {
  const { userId } = await auth();
  const baseUrl = getBaseUrl(request);

  if (!userId) {
    return NextResponse.json(
      {
        url: `/sign-in?redirect_url=${encodeURIComponent(`${baseUrl}/terminal/overview`)}`,
      },
      { status: 401 },
    );
  }

  const priceId = process.env.STRIPE_PRO_PRICE_ID;

  if (!priceId) {
    throw new Error("Missing STRIPE_PRO_PRICE_ID environment variable.");
  }

  const session = await getStripe().checkout.sessions.create({
    mode: "subscription",
    line_items: [
      {
        price: priceId,
        quantity: 1,
      },
    ],
    success_url: `${baseUrl}/terminal/overview?upgraded=true`,
    cancel_url: `${baseUrl}/terminal/overview`,
    metadata: {
      clerkUserId: userId,
    },
  });

  return NextResponse.json({ url: session.url });
}
