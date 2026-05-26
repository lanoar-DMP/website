import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/blog(.*)",
  "/api/card(.*)",
  "/api/macro",
  "/api/markets",
]);

const isProtectedProRoute = createRouteMatcher(["/terminal/(.*)/pro(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  if (isProtectedProRoute(request) && !isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};
