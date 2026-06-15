import { NextRequest, NextResponse } from "next/server";

function apiConfig() {
  return {
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
    apiSecret: process.env.API_SECRET_KEY,
  };
}

export async function POST(request: NextRequest) {
  const { apiUrl, apiSecret } = apiConfig();
  if (!apiUrl || !apiSecret) {
    return new NextResponse("API config missing", { status: 500 });
  }

  try {
    const body = await request.text();
    const res = await fetch(`${apiUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiSecret,
      },
      body,
    });

    return new NextResponse(await res.text(), {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
      },
    });
  } catch {
    return new NextResponse("Chat proxy error", { status: 502 });
  }
}
