import { NextRequest, NextResponse } from "next/server";

function apiConfig() {
  return {
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
    apiSecret: process.env.API_SECRET_KEY,
  };
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ doc_id: string }> }
) {
  const { apiUrl, apiSecret } = apiConfig();
  if (!apiUrl || !apiSecret) {
    return new NextResponse(JSON.stringify({ error: "API config missing" }), { status: 500 });
  }

  const { doc_id } = await params;

  try {
    const res = await fetch(`${apiUrl}/api/documents/${doc_id}`, {
      method: "DELETE",
      headers: {
        "X-API-Key": apiSecret,
      },
    });

    const data = await res.json();
    return new NextResponse(JSON.stringify(data), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    return new NextResponse(JSON.stringify({ error: err.message || "Proxy error" }), { status: 502 });
  }
}
