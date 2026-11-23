import { NextResponse } from "next/server";

function apiConfig() {
  return {
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
    apiSecret: process.env.API_SECRET_KEY,
  };
}

export async function GET() {
  const { apiUrl, apiSecret } = apiConfig();
  if (!apiUrl || !apiSecret) {
    return new NextResponse(JSON.stringify({ error: "API config missing" }), { status: 500 });
  }

  try {
    const res = await fetch(`${apiUrl}/api/documents`, {
      method: "GET",
      headers: {
        "X-API-Key": apiSecret,
      },
    });

    const data = await res.json();
    return new NextResponse(JSON.stringify(data), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Proxy error";
    return new NextResponse(JSON.stringify({ error: message }), { status: 502 });
  }
}
