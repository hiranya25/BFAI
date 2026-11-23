import { NextRequest, NextResponse } from "next/server";

/**
 * Optional site-wide password (HTTP Basic Auth).
 *
 * The /api/* routes forward requests to the backend with the server-side API key,
 * so anyone who can open the site can upload and delete documents. Set APP_PASSWORD
 * (and optionally APP_USERNAME, default "admin") to require a login. Unset = open site.
 */
export function proxy(request: NextRequest) {
  const password = process.env.APP_PASSWORD;
  if (!password) return NextResponse.next();

  const username = process.env.APP_USERNAME || "admin";
  const header = request.headers.get("authorization") ?? "";

  if (header.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const sep = decoded.indexOf(":");
      if (sep >= 0 && safeEqual(decoded.slice(0, sep), username) && safeEqual(decoded.slice(sep + 1), password)) {
        return NextResponse.next();
      }
    } catch {
      // Malformed header: fall through to the challenge.
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="DocIntel", charset="UTF-8"' },
  });
}

function safeEqual(a: string, b: string): boolean {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

export const config = {
  // Everything except Next.js build assets and the favicon.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
