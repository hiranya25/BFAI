import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest, context: { params: Promise<{ filename: string }> }) {
  const { filename } = await context.params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const apiSecret = process.env.API_SECRET_KEY;

  if (!apiUrl || !apiSecret) {
    return new NextResponse("API config missing", { status: 500 });
  }

  try {
    const res = await fetch(`${apiUrl}/api/pages/${filename}`, {
      headers: {
        "X-API-Key": apiSecret,
      },
    });

    if (!res.ok) {
      return new NextResponse("Image not found", { status: res.status });
    }

    const blob = await res.blob();
    return new NextResponse(blob, {
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "image/jpeg",
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (e) {
    return new NextResponse("Proxy error", { status: 500 });
  }
}
