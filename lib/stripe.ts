import Stripe from "stripe";

const globalForStripe = globalThis as typeof globalThis & {
  stripeClient?: Stripe;
};

function createStripeClient(): Stripe {
  const secretKey = process.env.STRIPE_SECRET_KEY;

  if (!secretKey) {
    throw new Error("Missing STRIPE_SECRET_KEY environment variable.");
  }

  return new Stripe(secretKey);
}

export function getStripe(): Stripe {
  if (!globalForStripe.stripeClient) {
    globalForStripe.stripeClient = createStripeClient();
  }

  return globalForStripe.stripeClient;
}
