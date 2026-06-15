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
    const formData = await request.formData();
    const res = await fetch(`${apiUrl}/api/upload`, {
      method: "POST",
      headers: {
        "X-API-Key": apiSecret,
      },
      body: formData,
    });

    return new NextResponse(res.body, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  } catch {
    return new NextResponse("Upload proxy error", { status: 502 });
  }
}
