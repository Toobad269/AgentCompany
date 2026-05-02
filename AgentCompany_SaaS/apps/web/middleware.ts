import { NextResponse, type NextRequest } from "next/server";

const buckets = new Map<string, { count: number; resetAt: number }>();

function getClientKey(request: NextRequest) {
  const forwardedFor = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const realIp = request.headers.get("x-real-ip");

  return forwardedFor || realIp || "local";
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/legacy") ||
    pathname === "/favicon.ico" ||
    pathname === "/api/health"
  ) {
    return NextResponse.next();
  }

  const windowMs = Number(process.env.RATE_LIMIT_WINDOW_MS || 60_000);
  const maxRequests = Number(process.env.RATE_LIMIT_MAX_REQUESTS || 300);
  const now = Date.now();
  const key = `${getClientKey(request)}:${pathname.startsWith("/api") ? "api" : "page"}`;
  const current = buckets.get(key);

  if (!current || current.resetAt <= now) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return NextResponse.next();
  }

  current.count += 1;

  if (current.count > maxRequests) {
    return NextResponse.json(
      {
        error: "Too many requests. Please wait a moment and try again."
      },
      {
        status: 429,
        headers: {
          "Retry-After": String(Math.ceil((current.resetAt - now) / 1000))
        }
      }
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!.*\\.).*)"]
};
